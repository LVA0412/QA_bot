import requests.exceptions

import base_handler
import logging
import messages as msgs
from qa_bot import messages as qa_msgs, states as qa_states
from admin_bot import messages as admin_msgs, states as admin_states

import psycopg2
from sentence_transformers import SentenceTransformer
import telebot
from telebot import custom_filters
import telebot.handler_backends as telebot_backends
import telebot.storage as storage
import typing

import question_answers


logger = logging.getLogger(__name__)


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


POSTGRES_HOST = '172.20.57.4'


class BaseHandlersController:
    """
    Обертка над telebot
    """
    TOKEN_PATH = './'

    def __init__(self):
        logger.info('Start HandlersController initializing')
        with open(f'{self.TOKEN_PATH}token') as file:
            token = file.read()
        # состояния хранятся в локальной памяти
        state_storage = storage.StateMemoryStorage()
        self.bot = telebot.TeleBot(token, state_storage=state_storage)
        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))

        pg_host = 'localhost' if __debug__ else POSTGRES_HOST
        self.conn = psycopg2.connect(f"dbname='qa' user='qa' host='{pg_host}' password='k9430J84hGe5'")
        self.conn.autocommit = True

        self.sentence_transformer = SentenceTransformer('cointegrated/rubert-tiny2')
        self.qa_manager = question_answers.QAManager(self.sentence_transformer, self.conn)

        self.handler_by_state = dict()
        self.init_handlers()
        self.init_commands()

        logger.info('Finished HandlersController initializing successfully')

    def switch_to_state(
            self, state: telebot_backends.State,
            message: telebot.types.Message,
            bot_message: typing.Optional[str] = None,
    ) -> telebot.types.Message:
        handler = self.handler_by_state[str(state)]
        handler.message = message
        return handler.switch_on_me(bot_message)

    def run(self):
        logger.info('Start polling bot')
        while True:
            try:
                self.bot.infinity_polling(timeout=10, long_polling_timeout=5)
                break
            except requests.exceptions.ReadTimeout as ex:
                logger.error(f'Caught ReadTimeout error {ex}, restarting polling')

    def init_commands(self):
        ...

    def init_handlers(self):
        """
        Инициализирует все хэндлеры состояний
        хэндлер запускается, когда юзер пишет сообщение, находясь в каком-либо состоянии
        хэндлеры пишут какие-то сообщения, затем пишут финальное сообщение и переключают
        в очередное состояние (возможно остается старое)
        """

        for subclass in all_subclasses(base_handler.BaseMessageHandler):
            if subclass.STATE is not None:
                handler = subclass(
                    self.bot,
                    self.qa_manager,
                    self.conn,
                )
                self.handler_by_state[str(handler.STATE)] = handler
                handler.set_handler_by_state(self.handler_by_state)


class QaHandlersController(BaseHandlersController):
    TOKEN_PATH = './qa_bot/'

    def init_commands(self):
        """
        здесь объявлены все команды
        если состояние не определено (пользователь пришел первый раз),
        то работают реализации, объявленные в этой функции, иначе реализации из base_handler
        """

        @self.bot.message_handler(commands=['start'])
        def start_handler(message: telebot.types.Message):
            self.switch_to_state(qa_states.STATE_BY_COMMAND['/start'], message)

        @self.bot.message_handler(commands=['help'])
        def help_handler(message: telebot.types.Message):
            self.bot.send_message(
                chat_id=message.chat.id,
                text=qa_msgs.HELP,
            )

        self.bot.set_my_commands([
            telebot.types.BotCommand('/start', 'Начало работы'),
            telebot.types.BotCommand('/help', 'Помощь'),
        ])

        @self.bot.message_handler(func=(lambda x: True))
        def misunderstand(message: telebot.types.Message):
            # дефолтный обработчик, если не подошел ни один другой
            self.switch_to_state(qa_states.BotStates.main, message, msgs.MISUNDERSTAND)


class AdminHandlersController(BaseHandlersController):
    TOKEN_PATH = './admin_bot/'

    def init_commands(self):
        """
        здесь объявлены все команды
        если состояние не определено (пользователь пришел первый раз),
        то работают реализации, объявленные в этой функции, иначе реализации из base_handler
        """

        @self.bot.message_handler(commands=['start'])
        def start_handler(message: telebot.types.Message):
            self.switch_to_state(admin_states.STATE_BY_COMMAND['/start'], message)

        @self.bot.message_handler(commands=['help'])
        def help_handler(message: telebot.types.Message):
            self.bot.send_message(
                chat_id=message.chat.id,
                text=admin_msgs.HELP,
            )

        self.bot.set_my_commands([
            telebot.types.BotCommand('/start', 'Начало работы'),
            telebot.types.BotCommand('/help', 'Помощь'),
            telebot.types.BotCommand('/list', 'Актуальный спиок вопросов'),
            telebot.types.BotCommand('/updates', 'Новые вопросы пользователей'),
            telebot.types.BotCommand('/connect', 'Выйти на линию'),
            telebot.types.BotCommand('/quit', 'Уйти с линии'),
        ])

        @self.bot.message_handler(func=(lambda x: True))
        def misunderstand(message: telebot.types.Message):
            # дефолтный обработчик, если не подошел ни один другой
            self.switch_to_state(admin_states.BotStates.main, message, msgs.MISUNDERSTAND)
