FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# --- Sistema ---
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# --- Clona SadTalker ---
RUN git clone https://github.com/Winfredy/SadTalker.git .

# --- Modelli SadTalker ---
RUN bash scripts/download_models.sh

# --- Dipendenze Python ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# (Extra safety) forza ffmpeg riconosciuto da imageio
ENV IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg

# --- Copia handler ---
COPY handler.py .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/usr/local/lib/python3.10/dist-packages:/app"

CMD ["python", "-u", "handler.py"]
