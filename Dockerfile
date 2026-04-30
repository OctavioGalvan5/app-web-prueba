FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc pkg-config libcairo2-dev libgirepository1.0-dev \
    libx11-dev libxcb1-dev libxrender-dev libxext-dev \
    libfreetype6-dev libfontconfig1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 3000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:3000", "--timeout", "120", "--workers", "2", "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]