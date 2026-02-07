import subprocess
import sys
import os

# 1. FORZIAMO L'INSTALLAZIONE DELLE LIBRERIE MANCANTI ALL'AVVIO
def install(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except:
        pass

install('safetensors')
install('boto3')
install('deepface')

import runpod
import boto3
import uuid
import glob
import shutil
import time
from deepface import DeepFace

# 2. CONFIGURAZIONE CLOUDFLARE R2
R2_ACCESS_KEY_ID = "006d152c1e6e968032f3088b90c330df"
R2_SECRET_ACCESS_KEY = "6a2549124d3b9205d83d959b214cc785" 
R2_BUCKET_NAME = "eccomionline-video"
R2_ENDPOINT_URL = "https://3320f2693994336c56f7093222830f6a.r2.cloudflarestorage.com"
R2_PUBLIC_URL = "https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev"

def handler(job):
    job_input = job['input']
    image_url = job_input.get('image_url')
    text = job_input.get('text')

    if not image_url or not text:
        return {"error": "Mancano image_url o text"}

    try:
        # Pulizia cartelle precedenti
        if os.path.exists('results'): shutil.rmtree('results')
        os.makedirs('results', exist_ok=True)

        # 3. DOWNLOAD FOTO
        os.system(f'curl -L -s -f "{image_url}" -o source.jpg')
        if not os.path.exists('source.jpg'):
            return {"error": "Impossibile scaricare la foto. Controlla il link."}

        # 4. ANALISI GENERE (DeepFace)
        try:
            objs = DeepFace.analyze(img_path="source.jpg", actions=['gender'], enforce_detection=False)
            gender = objs[0]['dominant_gender']
        except:
            gender = "Man"
        
        voice = "it-IT-GiuseppeNeural" if gender == "Man" else "it-IT-ElsaNeural"

        # 5. GENERAZIONE AUDIO (Edge-TTS)
        audio_cmd = f'edge-tts --text "{text}" --voice {voice} --write-media audio.wav'
        os.system(audio_cmd)

        # 6. RENDERING SADTALKER
        # Usiamo 'resize' per essere più veloci e stabili
        render_cmd = (
            f"python inference.py --source_image source.jpg --driven_audio audio.wav "
            f"--result_dir ./results --still --preprocess resize --enhancer gfpgan"
        )
        os.system(render_cmd)

        # 7. CARICAMENTO SU CLOUDFLARE R2
        mp4_files = glob.glob("results/**/*.mp4", recursive=True)
        if mp4_files:
            output_filename = f"{uuid.uuid4()}.mp4"
            s3 = boto3.client('s3',
                endpoint_url=R2_ENDPOINT_URL,
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY
            )
            s3.upload_file(mp4_files[0], R2_BUCKET_NAME, output_filename)
            
            video_url = f"{R2_PUBLIC_URL}/{output_filename}"
            return {"video_url": video_url}
        else:
            return {"error": "Video non generato. Controlla i log del rendering."}

    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
