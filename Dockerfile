FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Scarichiamo automaticamente tutto SadTalker dall'originale
RUN git clone https://github.com/Winfredy/SadTalker.git .

# 2. Installiamo le dipendenze di sistema
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && rm -rf /var/lib/apt/lists/*

# 3. Installiamo le librerie Python
RUN pip install --no-cache-dir runpod deepface edge-tts boto3 tf-keras opencv-python

# 4. Copiamo i tuoi file personalizzati sopra quelli di SadTalker
COPY handler.py .
COPY requirements.txt .

# 5. Creiamo la cartella per i risultati
RUN mkdir -p results

# Avvio del serverless
CMD ["python", "-u", "handler.py"]
