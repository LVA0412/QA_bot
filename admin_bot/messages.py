HELP = """Для начала работы нажмите /start
Чтобы выгрузить список вопросов, нажмите /list
Чтобы выгрузить новые вопросы пользователей, нажмите /updates
Чтобы загрузить обновленный список вопросов, отправьте сюда заполненный xlsx файл
Чтобы загрузить файл с ответом на вопрос (pdf, jpeg и т.п.), отправьте файл сюда
Чтобы начать принимать неотвеченные вопросы пользователей, нажмите /connect
Чтобы перестать принимать сообщения пользователей, нажмите /quit
Чтобы добавить других админов, нажмите /share и поделитесь сгенерированной инструкцией
Чтобы увидеть это сообщение еще раз, нажмите /help
"""

START_MESSAGE = 'Готов к работе! (нажмите /help, чтобы посмотреть подсказку еще раз)'

QUESTIONS_RENEWED = 'Список вопросов успешно загружен. Данные обновятся в течение одного часа (или последовательно введите команды /start /force_update_questions в AUDIT_TSBot)'

MISUNDERSTAND = 'Неизвестная команда. Нажмите /help для просмотра списка команд'

NO_PERMISSION = """Вас ещё нет в числе операторов поддержки. Возможно, присылаемый вами токен недействителен. Обратитесь к своему администратору для получения инструкций
Техническая информация: chat_id = {}.
"""

TOKEN_EXPIRED = 'Недействительный токен: время жизни истекло. Попросите новый токен у своего админитратора.'

PERM_ADDED = 'Вы успешно добавлены как оператор'

JOIN_INSTRUCTION = """Чтобы стать оператором поддержки:
1. Откройте чат с ботом по ссылке https://t.me/qa_support_admin_bot
2. Напишите <code>/start</code>
3. Отправьте сообщение с токеном <code>{}</code> . Больше ничего писать в сообщении не нужно
4. В ответ вам придет сообщение "{}" - это означает, что вы успешно добавлены. Если что-то пошло не так, обратитесь к своему администратору
Данный токен действителен в течение одного часа, но может быть сброшен раньше другим оператором
"""
