FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Installazione dipendenze di sistema e pulizia
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Clonazione SadTalker
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 3. Installazione librerie Python ignorando i conflitti di sistema
COPY requirements.txt .
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# 4. FIX CRITICO: Forziamo Numpy vecchio e Safetensors
# Questo risolve l'AttributeError VisibleDeprecationWarning e il modulo mancante
RUN pip install --no-cache-dir "numpy<2.0.0" "safetensors" "transformers==4.33.0"

COPY handler.py .
RUN mkdir -p results

CMD ["python", "-u", "handler.py"]
