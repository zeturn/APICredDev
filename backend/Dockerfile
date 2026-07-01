FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir poetry \
  && poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

RUN groupadd --system apicred && useradd --system --gid apicred --create-home --home-dir /home/apicred apicred

COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
RUN chown -R apicred:apicred /app
USER apicred
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8103/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8103"]

