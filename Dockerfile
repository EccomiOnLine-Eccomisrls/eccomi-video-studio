cat <<EOF > Dockerfile
FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel
WORKDIR /app
COPY . .
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6
RUN pip install runpod deepface edge-tts boto3 tf-keras opencv-python
CMD ["python", "-u", "handler.py"]
EOF
