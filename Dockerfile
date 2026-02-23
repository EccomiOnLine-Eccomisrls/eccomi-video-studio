FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# 1. Pulizia totale e preparazione cartelle
RUN rm -rf /tmp/custom_libs && mkdir -p /tmp/custom_libs

# 2. Dipendenze di sistema necessarie per la grafica
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Setup SadTalker
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# 4. InstallazioneRequirements e FIX delle librerie mancanti
# Installiamo scipy e numpy specifico subito, prima degli altri
RUN pip install --no-cache-dir "numpy==1.23.5" "scipy==1.11.0" "safetensors" "transformers==4.33.0"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .
RUN mkdir -p results

# Forziamo Python a ignorare le cartelle temporanee corrotte
ENV PYTHONPATH="/usr/local/lib/python3.10/dist-packages:/app"
ENV PIP_TARGET=""

CMD ["python", "-u", "handler.py"]
