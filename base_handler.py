import dataclasses
import logging
import typing

import telebot
import telebot.handler_backends as telebot_backends

import messages as msgs
from qa_bot import messages as qa_msgs
from qa_bot import states as qa_states
from admin_bot import messages as admin_msgs
from admin_bot import states as admin_states
from storage import queries
import question_answers


logger = logging.getLogger(__name__)


class BaseMessageHandler:

    DO_DEFAULT_COMMANDS = True
    STATE: typing.Optional[telebot_backends.State] = None
    STATE_BY_MESSAGE = dict()
    CONTENT_TYPES = ['text']

    def __init__(
            self,
            bot: telebot.TeleBot,
            qa_manager: question_answers.QAManager,
            conn,
    ):
        self.bot = bot
        self.qa_manager = qa_manager
        self.handler_by_state = None
        self.message: typing.Optional[telebot.types.Message] = None
        self.user_info = None
        self.conn = conn

        @bot.message_handler(state=self.STATE, content_types=self.CONTENT_TYPES)
        def _(message: telebot.types.Message):
            return self.handle_message_middleware(message)
            # if __debug__:
            #     # в debug режиме пробрасываем ошибку
            #     return self.handle_message_middleware(message)
            try:
                return self.handle_message_middleware(message)
            except Exception as ex:
                # Что бы ни случилось, не останавливаем поллинг
                logger.error(f'Caught exception {ex} while handling message '
                             f'{message} from user {message.from_user.username}'
                             f'(id={message.from_user.id})')

    @dataclasses.dataclass
    class MessageValidation:
        empty_message_enabled: bool = False
        prohibited_symbols: typing.Optional[typing.Set[str]] = None
        max_length: typing.Optional[int] = None

    validation = MessageValidation()

    def validate_message(self, message: telebot.types.Message) -> typing.Optional[telebot.types.Message]:
        if not self.validation.empty_message_enabled and not self.message:
            return self.try_again(msgs.EMPTY_TEXT_ERROR)
        if self.validation.prohibited_symbols is not None:
            if self.validation.prohibited_symbols & set(message.text):
                prohibited_symbol = list(self.validation.prohibited_symbols & set(message.text))[0]
                return self.try_again(msgs.PROHIBITED_CHARACTER.format(prohibited_symbol))
        if self.validation.max_length:
            if len(message.text) > self.validation.max_length:
                return self.try_again(msgs.TOO_LONG_NAME.format(self.validation.max_length))
        return None

    def set_handler_by_state(self, handler_by_state):
        self.handler_by_state = handler_by_state

    def handle_message_middleware(self, message: telebot.types.Message):
        """
        Do some middleware staff and call custom handling
        :param message: user message
        """
        logger.info(f'Got message {message.text} from user {message.from_user.id}')
        self.message = message
        reply_message = None
        if self.DO_DEFAULT_COMMANDS:
            # если введена команда и хэндлер поддерживает их обработку
            reply_message = self.check_and_switch_by_command()
            if reply_message is not None:
                return
        if reply_message is None:
            # если настроена валидация, то проверяем. В случае ошибки просим ввести заново
            reply_message = self.validate_message(message)
        if reply_message is None:
            # если состояние позволяет переходить в другие состояния по кнопкам, то делаем это
            reply_message = self.process_state_by_message(unknown_pass_enabled=True)
        if reply_message is None:
            # если все варианты выше не сработали, то запускаем хэндлер класса
            reply_message = self.handle_message(message)
        logger.info(f'Reply {reply_message} to user {message.from_user.username}')

    def check_and_switch_by_command(self) -> typing.Optional[telebot.types.Message]:
        # Переопределяется в наледниках
        return None

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        """
        Обработчик сообщения для конкретного состояния
        Релизация по умолчанию обрабатвает переходы по кнопкам
        (если не введен текст какой-либо кнопки, то просит ввести заново)
        :param message: сообщение пользователя
        :return: ответ
        """
        if not self.STATE_BY_MESSAGE:
            raise NotImplemented
        return self.process_state_by_message(unknown_pass_enabled=False)

    def switch_to_state(
            self, state: telebot_backends.State,
            message: typing.Optional[str] = None,
            markup: telebot.types.ReplyKeyboardMarkup = None,
            parse_mode: typing.Optional[str] = None,
    ) -> telebot.types.Message:
        handler = self.handler_by_state[str(state)]
        handler.message = self.message
        return handler.switch_on_me(message, markup=markup, parse_mode=parse_mode)

    def try_again(
            self, message: typing.Optional[str] = None,
            parse_mode: typing.Optional[str] = None,
            markup: telebot.types.ReplyKeyboardMarkup = None,
    ) -> telebot.types.Message:
        return self.switch_to_state(self.STATE, message, parse_mode=parse_mode, markup=markup)

    def process_state_by_message(
            self, unknown_pass_enabled=True,
    ) -> typing.Optional[telebot.types.Message]:
        message_text: str = ''
        if self.message.text is not None:
            message_text = self.message.text
        state_doc = self.STATE_BY_MESSAGE.get(message_text)
        if state_doc:
            return self.switch_to_state(
                state_doc['state'], state_doc.get('message'),
            )
        if not unknown_pass_enabled:
            markup = self.make_markup(self.make_buttons_list())
            return self.send_message(msgs.PARSE_BUTTON_ERROR, reply_markup=markup)
        return None

    MAX_MESSAGE_LENGTH = 4000

    def send_message(
            self, message: str, reply_markup=None, parse_mode=None,
    ) -> telebot.types.Message:
        max_iter = len(message) // self.MAX_MESSAGE_LENGTH + 1
        for i in range(max_iter):
            if i + 1 != max_iter:
                self.bot.send_message(
                    self.message.chat.id,
                    message[i * self.MAX_MESSAGE_LENGTH:(i + 1) * self.MAX_MESSAGE_LENGTH],
                    parse_mode=parse_mode, reply_markup=reply_markup,
                )
                continue
            return self.bot.send_message(
                self.message.chat.id, message[i * self.MAX_MESSAGE_LENGTH:],
                parse_mode=parse_mode, reply_markup=reply_markup,
            )

    def send_photo(
            self, photo_path: str,
    ) -> telebot.types.Message:
        photo = open(photo_path, 'rb')
        return self.bot.send_photo(self.message.chat.id, photo)

    DEFAULT_MESSAGE = None
    BUTTONS: typing.List[typing.List[str]] = []
    PARSE_MODE = None

    def switch_on_me(
            self,
            bot_message: str = None,
            markup: telebot.types.ReplyKeyboardMarkup = None,
            parse_mode: typing.Optional[str] = None,
    ) -> telebot.types.Message:
        """
        Update user's state and set appropriate buttons
        :param bot_message: message to send
        :param markup: markup to be set. Sets default of markup is None
        :param parse_mode: message parse mode e.g. MarkdownV2
        """
        if parse_mode is None:
            parse_mode = self.PARSE_MODE
        self.bot.set_state(
            self.message.from_user.id, self.STATE, self.message.chat.id,
        )
        if markup is None:
            markup = self.make_markup(self.make_buttons_list())
        if bot_message is None:
            bot_message = self.get_default_message()
            if bot_message is None:
                bot_message = 'Извините, произошла ошибка'
                logger.error(f'Попытка использовать неустановленное дефолтное сообщение для {self.STATE}')
        return self.send_message(bot_message, reply_markup=markup, parse_mode=parse_mode)

    @staticmethod
    def make_markup(buttons_list) -> telebot.types.ReplyKeyboardMarkup:
        if not buttons_list:
            return telebot.types.ReplyKeyboardRemove()
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=6)
        for row in buttons_list:
            markup.add(*[telebot.types.KeyboardButton(text) for text in row])
        return markup

    def get_default_message(self):
        return self.DEFAULT_MESSAGE

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        """
        Makes list of buttons to show on switch to this state
        """
        result_buttons = []
        for buttons_row in self.BUTTONS:
            new_buttons_row = []
            for button in buttons_row:
                new_buttons_row.append(button)
            if new_buttons_row:
                result_buttons.append(new_buttons_row)
        return result_buttons

    def set_user_cache(self, data: str):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.UPDATE_CACHE, (self.message.from_user.id, data, data))

    def get_user_cache(self) -> typing.Optional[str]:
        with self.conn.cursor() as cursor:
            cursor.execute(queries.READ_CACHE, (str(self.message.from_user.id), ))
            return cursor.fetchone()[0]

    def get_question_by_id(self, id: str) -> str:
        with self.conn.cursor() as cursor:
            cursor.execute(queries.GET_QUESTION_BY_ID, (id, ))
            return cursor.fetchone()[0]

    def upsert_answer(
            self,
            id: str,
            question: typing.Optional[str] = None,
            prev_question: typing.Optional[str] = None,
            answer: typing.Optional[str] = None,
            extra_info: typing.Optional[str] = None,
    ):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.UPSERT_QUESTION,
                (
                    id,
                    question, prev_question, extra_info, answer,
                    question, prev_question, extra_info, answer,
                ),
            )

    def save_question_answer(
            self,
            id: typing.Optional[str],
            question: str,
            text_answer: typing.Optional[str],
            file_answer: typing.Optional[str],
            ml_data: bytes,
    ):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.UPSERT_QUESTION_ANSWER,
                (
                    id,
                    question, text_answer, file_answer, ml_data,
                    question, text_answer, file_answer, ml_data,
                ),
            )

    def get_question_answers(self):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.GET_QUESTION_ANSWERS)
            rows = []
            while True:
                new_rows = cursor.fetchmany(1000)
                rows += new_rows
                if not new_rows:
                    break
        return rows

    def get_new_user_answers(self):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.GET_NEW_USER_QUESTIONS)
            rows = []
            while True:
                new_rows = cursor.fetchmany(1000)
                rows += new_rows
                if not new_rows:
                    break
        return rows

    def connect(self, user_id: str):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.CONNECT, (user_id, ))

    def quit(self, user_id: str):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.QUIT, (user_id, ))

    def get_user_question_by_id(self, question_id: str):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.GET_USER_QUESTION_BY_ID, (question_id, ))
            return cursor.fetchone()

    def get_operators(self) -> typing.List[int]:
        with self.conn.cursor() as cursor:
            cursor.execute(queries.GET_OPERATORS)
            rows = cursor.fetchmany(1000)
            return [int(row[0]) for row in rows]

    def check_operator(self) -> bool:
        with self.conn.cursor() as cursor:
            cursor.execute(queries.CHECK_OPERATOR, (str(self.message.chat.id), ))
            row = cursor.fetchone()
            return row and row[0] == 'ok'


class QaBaseHandler(BaseMessageHandler):
    def check_and_switch_by_command(self) -> typing.Optional[telebot.types.Message]:
        """
        If message start with command - switch to appropriate state
        and write a message
        :return: result message if swithed using a command and None otherwise
        """
        if not self.message.text.startswith('/'):
            return None
        if self.message.text == '/help':
            return self.try_again(qa_msgs.HELP)
        for command in qa_states.STATE_BY_COMMAND.keys():
            if self.message.text.startswith(command):
                state = qa_states.STATE_BY_COMMAND[command]
                return self.switch_to_state(state)
        return None


class AdminBaseHandler(BaseMessageHandler):
    def check_and_switch_by_command(self) -> typing.Optional[telebot.types.Message]:
        """
        Вроде бы не используется, т.к. всего одно состояние. Но на будущее надо оставить
        """
        if not self.message.text.startswith('/'):
            return None
        if self.message.text == '/help':
            return self.try_again(admin_msgs.HELP)
        for command in admin_states.STATE_BY_COMMAND.keys():
            if self.message.text.startswith(command):
                state = admin_states.STATE_BY_COMMAND[command]
                return self.switch_to_state(state)
        return None
