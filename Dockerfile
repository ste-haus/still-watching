FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY still_watching ./still_watching

EXPOSE 5553

# Run counts live in memory, so this must stay a single worker process.
CMD ["gunicorn", "--bind", "0.0.0.0:5553", "--workers", "1", "--threads", "4", "--access-logfile", "-", "still_watching.app:build()"]
