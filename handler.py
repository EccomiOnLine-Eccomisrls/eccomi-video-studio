import subprocess
import sys
import os

# FORZA L'INSTALLAZIONE PRIMA DI OGNI ALTRA COSA
subprocess.check_call([sys.executable, "-m", "pip", "install", "safetensors", "boto3", "deepface"])

import runpod
import boto3
import uuid
import glob
import shutil

# CONFIGURAZIONE R2 (Inserisci la tua Secret Key tra le virgolette)
R2_ACCESS_KEY_ID = "006d152c1e6e968032f3088b90c330df"
R2_SECRET_ACCESS_KEY = "6a2549124d3b9205d83d959b214cc785" 
R2_BUCKET_NAME = "eccomionline-video"
R2_ENDPOINT_URL = "https://3320f2693994336c56f7093222830f6a.r2.cloudflarestorage.com"
R2_PUBLIC_URL = "https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev"

def handler(job):
    from deepface import DeepFace
    job_input = job['input']
    image_url = job_input.get('image_url')
    text = job_input.get('text')

    try:
        if os.path.exists('results'): shutil.rmtree('results')
        os.makedirs('results', exist_ok=True)

        # Download immagine
        os.system(f'curl -L -s -f "{image_url}" -o source.jpg')
        
        # Analisi Genere
        objs = DeepFace.analyze(img_path="source.jpg", actions=['gender'], enforce_detection=False)
        voice = "it-IT-GiuseppeNeural" if objs[0]['dominant_gender'] == "Man" else "it-IT-ElsaNeural"

        # Generazione Audio e Video
        os.system(f'edge-tts --text "{text}" --voice {voice} --write-media audio.wav')
        os.system(f"python inference.py --source_image source.jpg --driven_audio audio.wav --result_dir ./results --still --preprocess resize --enhancer gfpgan")

        # Caricamento su R2
        mp4_files = glob.glob("results/**/*.mp4", recursive=True)
        if mp4_files:
            output_filename = f"{uuid.uuid4()}.mp4"
            s3 = boto3.client('s3', endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY)
            s3.upload_file(mp4_files[0], R2_BUCKET_NAME, output_filename)
            return {"video_url": f"{R2_PUBLIC_URL}/{output_filename}"}
        return {"error": "Video non generato"}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
