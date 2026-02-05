FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# Dipendenze di sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del progetto
COPY . .

# Avvio RunPod Serverless
CMD ["python", "handler.py"]
