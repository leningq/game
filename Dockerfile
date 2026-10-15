FROM python:3.13-slim

WORKDIR /app

# В контейнере нужен только сервер, без Pygame и окна игры.
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY api ./api
COPY game ./game
COPY templates ./templates
COPY static ./static

RUN mkdir -p /app/data
ENV BRICKFALL_DB_PATH=/app/data/brickfall.sqlite3
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
