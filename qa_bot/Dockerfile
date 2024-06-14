FROM python:3.7-slim-buster

WORKDIR /app/bot

COPY ./requirements.txt /app/.

RUN pip install -r /app/requirements.txt

COPY . /app/bot/.

ENV PYTHONPATH "${PYTHONPATH}:/app/bot"
