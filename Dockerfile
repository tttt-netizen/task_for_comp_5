FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY main.py ./
COPY settings.py ./
COPY shared ./shared
COPY landings ./landings
COPY core ./core
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

CMD ["uvicorn", "landings.main:app", "--host", "0.0.0.0", "--port", "8000"]
