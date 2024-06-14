import telebot.handler_backends as telebot_backends


class BotStates(telebot_backends.StatesGroup):
    main = telebot_backends.State()
    choose_question = telebot_backends.State()
    rewrite_question = telebot_backends.State()
    collect_contact_info = telebot_backends.State()


STATE_BY_COMMAND = {
    '/start': BotStates.main,
}
