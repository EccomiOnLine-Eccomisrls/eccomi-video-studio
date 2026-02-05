FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Installiamo Git e le librerie di sistema (Indispensabile!)
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. Ora scarichiamo SadTalker (Adesso Git funzionerà!)
RUN git clone https://github.com/Winfredy/SadTalker.git .

# 3. Installiamo le librerie Python
RUN pip install --no-cache-dir runpod deepface edge-tts boto3 tf-keras opencv-python

# 4. Copiamo i tuoi file personalizzati
COPY handler.py .
COPY requirements.txt .

# 5. Creiamo la cartella per i risultati
RUN mkdir -p results

CMD ["python", "-u", "handler.py"]
