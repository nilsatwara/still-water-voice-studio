FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_HOST=0.0.0.0 APP_PORT=8767
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r backend-requirements.txt
COPY backend ./backend
COPY audio_engine.py voice_catalog.py speech_text.py kokoro_worker.py ./
COPY data/voices.json ./data/voices.json
COPY models/kokoro ./models/kokoro
EXPOSE 8767
CMD ["python", "-m", "backend.app"]
