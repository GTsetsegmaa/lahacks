FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build context is the project root
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY agents/ ./agents/
COPY shared/  ./shared/

CMD ["python", "-m", "agents.run"]
