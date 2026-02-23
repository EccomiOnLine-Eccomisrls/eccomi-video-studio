FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Dipendenze di sistema
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. SadTalker Setup
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 3. Installazione Requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# 4. FIX DEFINITIVO PER NUMPY E SAFETENSORS
# Rimuoviamo numpy attuale e forziamo la versione 1.23.5 (stabile per SadTalker)
RUN pip uninstall -y numpy && \
    pip install --no-cache-dir "numpy==1.23.5" "safetensors" "transformers==4.33.0"

COPY handler.py .
RUN mkdir -p results

CMD ["python", "-u", "handler.py"]
