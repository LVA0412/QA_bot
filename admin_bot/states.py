import telebot.handler_backends as telebot_backends


class BotStates(telebot_backends.StatesGroup):
    main = telebot_backends.State()


STATE_BY_COMMAND = {
    '/start': BotStates.main,
}
