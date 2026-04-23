FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY apps /app/apps
COPY packages /app/packages
COPY scripts /app/scripts
COPY tests /app/tests
COPY docs /app/docs
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

RUN pip install --no-cache-dir -e .

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
