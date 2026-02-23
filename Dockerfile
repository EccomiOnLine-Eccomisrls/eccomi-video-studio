FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Installazione dipendenze di sistema e pulizia
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Clonazione SadTalker
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 3. Installazione librerie Python dal tuo requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# 4. FIX CRITICO: Forziamo le versioni compatibili per evitare crash (Numpy, Safetensors, Transformers)
# Questo risolve l'errore VisibleDeprecationWarning e il modulo mancante safetensors
RUN pip install --no-cache-dir "numpy<2.0.0" "safetensors" "transformers==4.33.0"

# 5. Copia del tuo handler e preparazione cartelle
COPY handler.py .
RUN mkdir -p results

# 6. Comando di avvio
CMD ["python", "-u", "handler.py"]
