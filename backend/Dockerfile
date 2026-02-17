FROM python:3.12-slim

ENV PYTHONDDONTWRITEBUCODE=1
ENV PYTHONBUFFERFERED=1
ENV code=123

WORKDIR /app

COPY requirements.txt
RUN pip install --nocache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

RUN useradd -m appuser
USER appuser

CMD ["python", "app.py"]