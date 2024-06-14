CREATE TABLE question_answers (
  id UUID PRIMARY KEY,
  question TEXT NOT NULL,
  text_answer TEXT,
  answer_file_path TEXT,
  ml_data BYTEA
);

CREATE TYPE QUESTION_STATUS AS ENUM('created', 'accepted', 'processed', 'rejected');

CREATE TABLE user_questions (
  id UUID PRIMARY KEY,
  question TEXT NOT NULL,
  previous_question TEXT,
  created timestamp NOT NULL,
  found_answer_id UUID,
  extra_info TEXT,
  question_status QUESTION_STATUS,
  FOREIGN KEY (found_answer_id) REFERENCES question_answers(id)
);

CREATE TABLE users_cache (
    user_id TEXT PRIMARY KEY,
    data TEXT
);

CREATE TYPE operator_status AS ENUM('online', 'offline');

CREATE TABLE operators (
    user_id TEXT PRIMARY KEY,
    status operator_status NOT NULL DEFAULT 'offline';
);

-- admin pg pass g23fKj8%d2
-- bot pg pass k9430J84hGe5