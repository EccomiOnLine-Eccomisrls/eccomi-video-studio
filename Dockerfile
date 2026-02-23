FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. CANCELLAZIONE FISICA DELLA CACHE CORROTTA (Fondamentale)
RUN rm -rf /tmp/custom_libs && mkdir -p /tmp/custom_libs

# 2. Dipendenze di sistema
RUN apt-get update && apt-get install -y \
    git ffmpeg libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Setup SadTalker
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 4. Installazione pulita (Usiamo python3 -m pip per sicurezza)
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir --upgrade pip
RUN python3 -m pip install --no-cache-dir "numpy<2.0.0" "transformers==4.33.0"
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY handler.py .
RUN mkdir -p results

# Impediamo a Python di guardare nella cartella temporanea maledetta
ENV PYTHONPATH="/usr/local/lib/python3.10/dist-packages:/app"
ENV PIP_TARGET=""

CMD ["python3", "-u", "handler.py"]
