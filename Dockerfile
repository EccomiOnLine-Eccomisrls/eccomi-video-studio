# Cambiamo immagine base con una più completa e stabile
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Installazione dipendenze di sistema (senza fronzoli)
RUN apt-get update && apt-get install -y \
    git ffmpeg libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup SadTalker
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 3. Installazione forzata delle versioni compatibili
# Usiamo l'indirizzo assoluto di pip per evitare l'errore "not found"
RUN /usr/bin/python3 -m pip install --upgrade pip
RUN /usr/bin/python3 -m pip install --no-cache-dir "numpy<2.0.0" "scipy<1.13.0" "safetensors" "transformers==4.33.0"

# 4. Resto dei requisiti
COPY requirements.txt .
RUN /usr/bin/python3 -m pip install --no-cache-dir -r requirements.txt

COPY handler.py .
RUN mkdir -p results

# Comando di avvio con percorso assoluto
CMD ["/usr/bin/python3", "-u", "handler.py"]
