FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

WORKDIR /app

# ===============================
# Sistema base
# ===============================
RUN apt-get update && apt-get install -y \
    git ffmpeg curl libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# Clona SadTalker
# ===============================
RUN git clone https://github.com/Winfredy/SadTalker.git .
RUN bash scripts/download_models.sh

# ===============================
# Patch FIX BUG imageio fps
# ===============================
RUN sed -i "s/imageio.mimsave(path, result, fps=float(25))/import imageio\nfps=25\nif str(path).lower().endswith('.mp4'):\n    writer=imageio.get_writer(path,fps=fps)\n    [writer.append_data(frame) for frame in result]\n    writer.close()\nelse:\n    imageio.mimsave(path,result)/" src/facerender/animate.py

# ===============================
# Installa dipendenze handler
# ===============================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===============================
# Forza versioni stabili SadTalker
# ===============================
RUN pip install --no-cache-dir \
    numpy==1.23.5 \
    transformers==4.33.0 \
    scipy==1.11.0 \
    safetensors \
    imageio==2.34.0 \
    imageio-ffmpeg==0.4.9 \
    tifffile==2023.7.10

# ===============================
# Copia handler RunPod
# ===============================
COPY handler.py .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/usr/local/lib/python3.10/dist-packages:/app"

CMD ["python", "-u", "handler.py"]
