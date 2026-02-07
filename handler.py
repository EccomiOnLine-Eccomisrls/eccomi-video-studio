import runpod
import os
import boto3
import uuid
import glob
import shutil
import time

# CONFIGURAZIONE R2
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

        # 1. SCARICAMENTO FOTO CON ATTESA
        os.system(f'curl -L -s -f "{image_url}" -o source.jpg')
        
        # Aspettiamo massimo 5 secondi che il file appaia sul disco
        for _ in range(5):
            if os.path.exists('source.jpg'): break
            time.sleep(1)

        if not os.path.exists('source.jpg'):
            return {"error": "Errore critico: la foto non è stata scaricata. Controlla il link."}

        # 2. ANALISI E GENERAZIONE
        objs = DeepFace.analyze(img_path="source.jpg", actions=['gender'], enforce_detection=False)
        voice = "it-IT-GiuseppeNeural" if objs[0]['dominant_gender'] == "Man" else "it-IT-ElsaNeural"

        os.system(f'edge-tts --text "{text}" --voice {voice} --write-media audio.wav')
        
        # Rendering SadTalker
        os.system(f"python inference.py --source_image source.jpg --driven_audio audio.wav --result_dir ./results --still --preprocess resize --enhancer gfpgan")

        # 3. CARICAMENTO SU R2
        mp4_files = glob.glob("results/**/*.mp4", recursive=True)
        if mp4_files:
            output_filename = f"{uuid.uuid4()}.mp4"
            s3 = boto3.client('s3', endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY)
            s3.upload_file(mp4_files[0], R2_BUCKET_NAME, output_filename)
            return {"video_url": f"{R2_PUBLIC_URL}/{output_filename}"}
        
        return {"error": "Rendering fallito. Controlla i parametri dell'immagine."}

    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
