import dataclasses
import typing
import uuid

import numpy
import openpyxl
import pandas as pd
import datetime


@dataclasses.dataclass
class QuestionAnswer:
    id: typing.Optional[str]
    question: str
    text_answer: typing.Optional[str]
    answer_file_path: typing.Optional[str]


@dataclasses.dataclass
class NewUserQuestion:
    question: str
    previous_question: typing.Optional[str]
    created: datetime.datetime
    extra_info: typing.Optional[str]


def empty(value):
    return not value or value == numpy.nan


def parse_xlsx(filename: str) -> typing.List[QuestionAnswer]:

    wb = openpyxl.load_workbook(filename)
    sheet = wb.active  # загружаем первую страницу

    results = []
    for row in sheet.iter_rows(min_row=2, values_only=True):  # пропускаем заголовки
        id = row[0] if row[0] else None
        question = row[1]
        text_answer = row[2] if row[2] else None
        answer_file_path = row[3] if row[3] else None

        question_answer = QuestionAnswer(
            id=id,
            question=question,
            text_answer=text_answer,
            answer_file_path=answer_file_path
        )
        if question_answer.id is None:
            question_answer.id = uuid.uuid4().hex
        if question_answer.text_answer is None and question_answer.answer_file_path is None:
            # пропускаем неполные ответы
            continue
        results.append(question_answer)

    wb.close()
    return results


def write_question_answer_to_xlsx(questions_answers: typing.List[QuestionAnswer], file_path: str):
    data = {
        'id': [qa.id for qa in questions_answers],
        'Вопрос': [qa.question for qa in questions_answers],
        'Текстовый ответ': [qa.text_answer for qa in questions_answers],
        'Ответ в виде файла': [qa.answer_file_path for qa in questions_answers]
    }

    df = pd.DataFrame(data)

    df.to_excel(file_path, index=False)


def write_new_questions_to_xlsx(questions_answers: typing.List[NewUserQuestion], file_path: str):
    data = {
        'Время создания': [qa.created for qa in questions_answers],
        'Вопрос': [qa.question for qa in questions_answers],
        'Другая формулировка': [qa.previous_question for qa in questions_answers],
        'Контактная информация': [qa.extra_info for qa in questions_answers]
    }

    df = pd.DataFrame(data)

    df.to_excel(file_path, index=False)
