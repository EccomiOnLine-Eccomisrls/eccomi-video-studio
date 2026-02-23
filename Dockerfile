FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Dipendenze di sistema fondamentali
RUN apt-get update && apt-get install -y \
    git ffmpeg libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup SadTalker (Clonazione pulita)
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 3. Installazione forzata dei componenti critici (Scipy e Numpy stabile)
RUN python3 -m pip install --no-cache-dir --upgrade pip
RUN python3 -m pip install --no-cache-dir "numpy==1.23.5" "scipy==1.11.0" "safetensors" "transformers==4.33.0"

# 4. Installazione del resto dei requisiti
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY handler.py .
RUN mkdir -p results

# Comando di avvio esplicito
CMD ["python3", "-u", "handler.py"]
