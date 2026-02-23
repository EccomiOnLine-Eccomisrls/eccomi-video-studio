FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. ELIMINAZIONE FORZATA DELLE LIBRERIE CORROTTE (Il colpevole del crash)
RUN rm -rf /tmp/custom_libs && mkdir -p /tmp/custom_libs

# 2. Dipendenze di sistema
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 3. SadTalker Setup
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 4. Installazione Requirements pulita
COPY requirements.txt .
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# 5. BLOCCO VERSIONI (Numpy 1.23.5 è l'unica che funziona con SadTalker)
RUN pip uninstall -y numpy && \
    pip install --no-cache-dir "numpy==1.23.5" "safetensors" "transformers==4.33.0"

COPY handler.py .
RUN mkdir -p results

# Forziamo Python a usare le librerie di sistema e NON quelle in /tmp
ENV PYTHONPATH="/usr/local/lib/python3.10/dist-packages:/app"
ENV PIP_TARGET=""

CMD ["python", "-u", "handler.py"]
