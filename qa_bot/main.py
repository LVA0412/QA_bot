import datetime
import io
import uuid

import telebot.types

import states
from base_handler import QaBaseHandler
import controller
import qa_bot.messages as msgs
from states import BotStates
from admin_bot import xlsx_util


class MainStateHandler(QaBaseHandler):
    # Корневой хэндлер. Запускается при начале работы и при нажатии на /start
    STATE = BotStates.main
    DEFAULT_MESSAGE = msgs.HELLO

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == '/force_update_questions':
            self.qa_manager.renew_data()
            return self.try_again('Список вопросов обновлен.')
        question_id = uuid.uuid4().hex
        self.set_user_cache(question_id)
        self.upsert_answer(question_id, question=message.text)

        suggestions = self.qa_manager.suggest(message.text)
        if not suggestions:
            return self.switch_to_state(states.BotStates.rewrite_question)
        if len(suggestions) == 1:
            suggestion = suggestions[0]
            self.upsert_answer(question_id, question=message.text, answer=suggestion.id)
            text_answer = suggestion.answer
            if suggestion.file_answer:
                with open(f'./files/{suggestion.file_answer}', 'rb') as file:
                    content = file.read()
                    file_obj = io.BytesIO(content)
                    file_obj.name = suggestion.file_answer
                    self.bot.send_document(self.message.chat.id, file_obj)
                if not suggestion._answer:
                    text_answer = 'Ответ можно найти во вложении'
            return self.try_again(text_answer)
        suggestions = suggestions[:3]
        markup = self.make_markup(
            [
                [suggestion.short_question]
                for suggestion in suggestions
            ] + [[msgs.NOTHING_ACCEPTABLE]]
        )
        same_questions_list = ''
        for i, qa in enumerate(suggestions):
            same_questions_list += f'\n{i + 1}. {qa.question}'
        answer = msgs.MANY_ANSWERS.format(same_questions_list)
        return self.switch_to_state(
            states.BotStates.choose_question, answer, markup=markup,
        )


class ChooseQuestion(QaBaseHandler):
    # Пользователь выбирает один вопрос из похожих
    STATE = BotStates.choose_question

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == msgs.NOTHING_ACCEPTABLE:
            return self.switch_to_state(states.BotStates.rewrite_question)
        suggestion = self.qa_manager.get_by_short_question(message.text)
        if suggestion:
            question_id = self.get_user_cache()
            self.upsert_answer(question_id, answer=suggestion.id)
            text_answer = suggestion.answer
            if suggestion.file_answer:
                with open(f'./files/{suggestion.file_answer}', 'rb') as file:
                    content = file.read()
                    file_obj = io.BytesIO(content)
                    file_obj.name = suggestion.file_answer
                    self.bot.send_document(self.message.chat.id, file_obj)
                if not suggestion._answer:
                    text_answer = 'Ответ можно найти во вложении'
            return self.switch_to_state(BotStates.main, text_answer)
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class RewriteQuestion(QaBaseHandler):
    # Пользователь формулирует заново вопрос
    STATE = BotStates.rewrite_question
    DEFAULT_MESSAGE = msgs.REWRITE_QUESTION

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        question_id = self.get_user_cache()
        prev_question = self.get_question_by_id(question_id)
        self.upsert_answer(question_id, question=message.text, prev_question=prev_question)

        suggestions = self.qa_manager.suggest(message.text)
        if not suggestions:
            return self.switch_to_state(states.BotStates.collect_contact_info)
        if len(suggestions) == 1:
            suggestion = suggestions[0]
            self.upsert_answer(question_id, question=message.text, answer=suggestion.id)
            text_answer = suggestion.answer
            if suggestion.file_answer:
                with open(f'./files/{suggestion.file_answer}', 'rb') as file:
                    content = file.read()
                    file_obj = io.BytesIO(content)
                    file_obj.name = suggestion.file_answer
                    self.bot.send_document(self.message.chat.id, file_obj)
                if not suggestion._answer:
                    text_answer = 'Ответ можно найти во вложении'
            return self.switch_to_state(BotStates.main, text_answer)
        suggestions = suggestions[:3]
        markup = self.make_markup(
            [
                [suggestion.short_question]
                for suggestion in suggestions
            ] + [[msgs.NOTHING_ACCEPTABLE]]
        )
        same_questions_list = ''
        for i, qa in enumerate(suggestions):
            same_questions_list += f'\n{i + 1}. {qa.question}'
        answer = msgs.MANY_ANSWERS.format(same_questions_list)
        return self.switch_to_state(
            states.BotStates.choose_question, answer, markup=markup,
        )


class CollectContactInfo(QaBaseHandler):
    # Пользователь пишет, как с ним можно связаться
    STATE = BotStates.collect_contact_info
    DEFAULT_MESSAGE = msgs.CONTACT_INFO_REQUEST

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        question_id = self.get_user_cache()

        self.upsert_answer(question_id, extra_info=message.text)

        raw_question = self.get_user_question_by_id(question_id)
        question = xlsx_util.NewUserQuestion(
            question=raw_question[0],
            previous_question=raw_question[1],
            created=raw_question[2],
            extra_info=raw_question[3],
        )
        question.created = datetime.datetime.replace(question.created, microsecond=0)
        for operator_chat_id in self.get_operators():
            self.bot.send_message(
                operator_chat_id,
                msgs.TO_OPERATOR.format(
                    question.question,
                    question.previous_question,
                    str(question.created),
                    question.extra_info,
                ),
            )

        return self.switch_to_state(states.BotStates.main, msgs.START_AGAIN)


if __name__ == '__main__':
    controller = controller.QaHandlersController()
    controller.run()
