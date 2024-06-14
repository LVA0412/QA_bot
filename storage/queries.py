UPDATE_CACHE = """
INSERT INTO users_cache (user_id, data)
VALUES (%s, %s)
ON CONFLICT (user_id) DO UPDATE
SET data = %s;
"""

READ_CACHE = """
SELECT data FROM users_cache WHERE user_id = %s;
"""

UPSERT_QUESTION = """
INSERT INTO user_questions(id, question, previous_question, created, question_status, extra_info, found_answer_id)
VALUES
(%s, COALESCE(%s, ''), %s, NOW(), 'created', %s, %s)
ON CONFLICT (id) DO UPDATE
SET 
question = COALESCE(%s, user_questions.question),
previous_question = COALESCE(%s, user_questions.previous_question),
extra_info = COALESCE(%s, user_questions.extra_info),
found_answer_id = COALESCE(%s, user_questions.found_answer_id);
"""

UPSERT_QUESTION_ANSWER = """
INSERT INTO question_answers(id, question, text_answer, answer_file_path, ml_data)
VALUES
(%s, %s, %s, %s, %s)
ON CONFLICT(id) DO UPDATE
SET 
question = %s,
text_answer = %s,
answer_file_path = %s,
ml_data = %s;
"""

GET_QUESTION_BY_ID = """
SELECT question
FROM user_questions
WHERE id = %s;
"""

GET_QUESTION_ANSWERS = """
SELECT id, question, text_answer, answer_file_path
FROM question_answers;
"""

GET_NEW_USER_QUESTIONS = """
UPDATE user_questions
SET question_status = 'processed'
WHERE question_status = 'created' and found_answer_id IS NULL
RETURNING question, previous_question, created, extra_info;
"""

GET_INIT_QUESTION_ANSWERS = """
SELECT id, question, text_answer, answer_file_path, ml_data
FROM question_answers;
"""

CONNECT = """
INSERT INTO operators (user_id, status)
VALUES (%s, 'online'::operator_status)
ON CONFLICT(user_id) DO UPDATE
SET status = 'online'::operator_status;
"""

QUIT = """
INSERT INTO operators (user_id, status)
VALUES (%s, 'offline'::operator_status)
ON CONFLICT(user_id) DO UPDATE
SET status = 'offline'::operator_status;
"""

CHECK_OPERATOR = """
SELECT 'ok'
FROM operators
WHERE user_id = %s;
"""

GET_OPERATORS = """
SELECT user_id FROM operators WHERE status = 'online';
"""

GET_USER_QUESTION_BY_ID = """
SELECT question, previous_question, created, extra_info
from user_questions
where id = %s;
"""

