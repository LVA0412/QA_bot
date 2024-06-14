import datetime
import io
import uuid

import telebot.types

from base_handler import AdminBaseHandler
import controller
import admin_bot.messages as msgs
from states import BotStates
import xlsx_util
import os


TOKEN_UPDATED = datetime.datetime.now()
JOIN_TOKEN = uuid.uuid4().hex


class MainStateHandler(AdminBaseHandler):
    # Единственный хэндлер, который делает всю работу
    DO_DEFAULT_COMMANDS = False  # чтобы здесь обрабатывать команды
    STATE = BotStates.main
    DEFAULT_MESSAGE = msgs.START_MESSAGE
    CONTENT_TYPES = ['text', 'document', 'photo']

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        global JOIN_TOKEN, TOKEN_UPDATED
        current_token = JOIN_TOKEN
        if self.message.text == current_token:
            if datetime.datetime.now() > TOKEN_UPDATED + datetime.timedelta(hours=1):
                return self.try_again(msgs.TOKEN_EXPIRED)
            self.quit(str(self.message.chat.id))  # Добавляет в таблицу со статусом offline
            return self.try_again(msgs.PERM_ADDED)

        if not self.check_operator():
            return self.try_again(msgs.NO_PERMISSION.format(message.chat.id))

        if message.document is not None and message.document.file_id is not None:
            if message.document.file_name.endswith('.xlsx'):
                file_info = self.bot.get_file(message.document.file_id)
                downloaded_file = self.bot.download_file(file_info.file_path)
                with open('./admin_bot/tmp/questions.xlsx', 'wb') as new_file:
                    new_file.write(downloaded_file)
                questions = xlsx_util.parse_xlsx('./admin_bot/tmp/questions.xlsx')
                os.remove('./admin_bot/tmp/questions.xlsx')
                for question in questions:
                    encoding = self.qa_manager.st.encode(question.question)
                    ml_data = encoding.tobytes()
                    self.save_question_answer(
                        question.id, question.question, question.text_answer, question.answer_file_path, ml_data,
                    )

                return self.try_again(msgs.QUESTIONS_RENEWED)
            else:
                file_info = self.bot.get_file(message.document.file_id)
                downloaded_file = self.bot.download_file(file_info.file_path)
                with open(f'./files/{message.document.file_name}', 'wb') as new_file:
                    new_file.write(downloaded_file)
                return self.try_again(
                    f'Файл успешно сохранен. '
                    f'Чтобы использовать его в качестве ответа на вопрос, '
                    f'укажите в поле "Ответ в виде файла" значение "{message.document.file_name}".',
                )
        if message.text == '/help':
            return self.try_again(msgs.HELP)
        if message.text == '/share':
            JOIN_TOKEN = uuid.uuid4().hex
            TOKEN_UPDATED = datetime.datetime.now()
            return self.try_again(msgs.JOIN_INSTRUCTION.format(JOIN_TOKEN, msgs.PERM_ADDED), parse_mode='HTML')
        if message.text == '/start':
            return self.try_again(msgs.START_MESSAGE)
        if message.text == '/list':
            rows = self.get_question_answers()
            question_answers = [
                xlsx_util.QuestionAnswer(
                    id=row[0],
                    question=row[1],
                    text_answer=row[2],
                    answer_file_path=row[3],
                )
                for row in rows
            ]
            xlsx_util.write_question_answer_to_xlsx(question_answers, './admin_bot/tmp/questions_export.xlsx')
            with open('./admin_bot/tmp/questions_export.xlsx', 'rb') as file:
                content = file.read()
                file_obj = io.BytesIO(content)
                file_obj.name = "Список_вопросов.xlsx"
                self.bot.send_document(self.message.chat.id, file_obj)
            return self.try_again(msgs.START_MESSAGE)
        if message.text == '/updates':
            rows = self.get_new_user_answers()
            new_questions = [
                xlsx_util.NewUserQuestion(
                    question=row[0],
                    previous_question=row[1],
                    created=row[2],
                    extra_info=row[3],
                )
                for row in rows
            ]
            new_questions = sorted(new_questions, key=lambda x: x.created)
            xlsx_util.write_new_questions_to_xlsx(new_questions, './admin_bot/tmp/new_questions_export.xlsx')
            with open('./admin_bot/tmp/new_questions_export.xlsx', 'rb') as file:
                content = file.read()
                file_obj = io.BytesIO(content)
                file_obj.name = "Вопросы_пользователей.xlsx"
                self.bot.send_document(self.message.chat.id, file_obj)
            return self.try_again(msgs.START_MESSAGE)
        if message.text == '/connect':
            self.connect(str(message.chat.id))
            return self.try_again('Вы вышли на линию')
        if message.text == '/quit':
            self.quit(str(message.chat.id))
            return self.try_again('Вы вышли с линии')
        return self.try_again(msgs.MISUNDERSTAND)


if __name__ == '__main__':
    controller = controller.AdminHandlersController()
    controller.run()
