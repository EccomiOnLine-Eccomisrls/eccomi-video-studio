FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Ripristino dipendenze di sistema originali
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup SadTalker (versione originale)
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 3. Installazione Requirements (con le versioni che SadTalker "ama")
COPY requirements.txt .
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# 4. IL PONTE DI COMANDO: Forziamo le versioni esatte per fermare l'AttributeError
# Numpy 1.23.5 e Transformers 4.33.0 riportano il sistema allo stato stabile precedente
RUN pip uninstall -y numpy && \
    pip install --no-cache-dir "numpy==1.23.5" "safetensors" "transformers==4.33.0" "scipy==1.11.0"

COPY handler.py .
RUN mkdir -p results

# Assicuriamoci che il sistema usi le librerie appena installate
ENV PYTHONPATH="/usr/local/lib/python3.10/dist-packages:/app"

CMD ["python", "-u", "handler.py"]
