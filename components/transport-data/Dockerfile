FROM python:3.12-slim

WORKDIR /app
COPY components/transport-data/refresh.py /app/refresh.py
COPY components/transport-data/sources.json /app/sources.json

ENTRYPOINT ["python", "/app/refresh.py"]
