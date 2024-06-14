FROM python:3.7-slim-buster

WORKDIR /app/bot

RUN mkdir -p /app/bot/admin_bot/tmp

COPY ./requirements.txt /app/.

RUN pip install -r /app/requirements.txt

COPY . /app/bot/.

ENV PYTHONPATH "${PYTHONPATH}:/app/bot"
