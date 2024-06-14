import csv
import dataclasses
import datetime
import logging
import typing

import numpy
import numpy as np
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer
from storage import queries

from qa_bot import messages as msgs

logger = logging.getLogger(__name__)


SHORT_QUESTION_LEN = 40


@dataclasses.dataclass
class QuestionAnswer:
    id: str
    question: str
    encoding: numpy.ndarray
    _answer: typing.Optional[str] = None
    file_answer: typing.Optional[str] = None

    @property
    def answer(self):
        if self._answer:
            return self._answer
        return msgs.QUESTION_WO_ANSWER

    @property
    def short_question(self):
        if len(self.question) < SHORT_QUESTION_LEN:
            return self.question
        return self.question[:SHORT_QUESTION_LEN] + '...'


class QAManager:
    CSV_SOURCE = '../qa_clear.csv'
    ACCEPTABLE_THRESHOLD = 0.25

    def __init__(self, st: SentenceTransformer, conn):
        self._qas = {}
        self.st = st
        self._by_short_question = {}
        self.conn = conn
        logger.info('Start initialize corpus')
        self.renew_data()
        logger.info('Finished initializing corpus successfully')
        self.last_renew_dt = datetime.datetime.now()

    def renew_data(self):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.GET_INIT_QUESTION_ANSWERS)
            rows = []
            while True:
                new_rows = cursor.fetchmany(1000)
                rows += new_rows
                if not new_rows:
                    break
        for row in rows:
            id = row[0]
            qa = QuestionAnswer(
                id=id,
                question=row[1],
                _answer=row[2],
                file_answer=row[3],
                encoding=np.frombuffer(row[4], dtype=np.float32),
            )
            self._qas[id] = qa
            self._by_short_question[qa.short_question] = self._qas[id]

    def suggest(self, user_question: str):
        """
        :param user_question: текст
        :return: список вопросов-ответов, где вопросы наиболее похожи на
        данный текст. Отсортированы по убыванию актуальности. Неактуальные исключены
        """
        if datetime.datetime.now() > self.last_renew_dt + datetime.timedelta(hours=1):
            self.renew_data()
            self.last_renew_dt = datetime.datetime.now()
        from_user_encoding = self.st.encode(user_question)
        scores_w_ids = [
            (cosine(from_user_encoding, q.encoding), q.id)
            for q in self._qas.values()
        ]
        scores_w_ids = sorted(scores_w_ids, key=lambda x: x[0])
        acceptable_ids = [
            score_w_id[1]
            for score_w_id in scores_w_ids
            if score_w_id[0] <= self.ACCEPTABLE_THRESHOLD
        ]
        return [
            self.get_by_id(qa_id)
            for qa_id in acceptable_ids
        ]

    def get_by_id(self, id: int) -> typing.Optional[QuestionAnswer]:
        return self._qas.get(id)

    def get_by_short_question(self, short_question: str) -> typing.Optional[QuestionAnswer]:
        return self._by_short_question.get(short_question)

    def get_as_list(self) -> typing.Iterable[QuestionAnswer]:
        return self._qas.values()
