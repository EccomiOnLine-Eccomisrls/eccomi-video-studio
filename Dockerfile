FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .
RUN mkdir -p results

CMD ["python", "-u", "handler.py"]

