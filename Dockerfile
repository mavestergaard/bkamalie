FROM python:3.12-slim

EXPOSE 8501

WORKDIR /app
COPY . /app

RUN pip install hatch && hatch env create default

CMD hatch run app
