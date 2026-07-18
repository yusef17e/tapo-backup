FROM python:3.12-slim

# FFmpeg is required by pytapo to process SD card recordings
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY tapo-drive-backup/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tapo-drive-backup/ .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
