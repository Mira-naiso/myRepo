FROM python:3.9-slim

ARG GITHUB_CREDS

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc make python3-dev git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN git config --global url."https://${GITHUB_CREDS}@github.com/inDriver".insteadOf "https://github.com/inDriver"

WORKDIR /app

COPY requirements.txt /app/
RUN python -m venv /app/.venv && \
    . /app/.venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
COPY config/ /app/

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "pagerduty-reminder.py"]
