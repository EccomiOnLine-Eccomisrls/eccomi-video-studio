FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Dipendenze di sistema
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    curl \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. Scarichiamo SadTalker
RUN git clone https://github.com/Winfredy/SadTalker.git .

# 3. SCARICHIAMO I MODELLI (Questo è quello che mancava!)
RUN bash scripts/download_models.sh

# 4. Installiamo le librerie Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gdown 

# 5. Copiamo il tuo codice
COPY handler.py .

RUN mkdir -p results

CMD ["python", "-u", "handler.py"]
