import runpod
import os
import boto3
import uuid
from deepface import DeepFace

# CONFIGURAZIONE CLOUDFLARE R2 (Inserisco i tuoi dati già testati)
ACCESS_KEY = "6a2549124d3b9205d83d959b214cc785"
SECRET_KEY = "7cd7656140d6379abdfbc21df448478f87a32afdc613f4d32c53e5bbc3541bf8"
ENDPOINT_URL = "https://b9fa6928f7ee48bcac3b22e0665726e1.r2.cloudflarestorage.com"
BUCKET_NAME = "eccomionline-video"

def upload_to_r2(file_path, job_id):
    s3 = boto3.client('s3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="auto"
    )
    filename = f"{job_id}.mp4"
    s3.upload_file(file_path, BUCKET_NAME, filename, ExtraArgs={'ContentType': 'video/mp4'})
    # Questo è il link pubblico che userai per inviare il video al cliente
    return f"https://pub-b9fa6928f7ee48bcac3b22e0665726e1.r2.dev/{filename}"

def handler(job):
    try:
        data = job["input"]
        image_url = data.get("image_url")
        text = data.get("text")
        job_id = job.get("id", str(uuid.uuid4()))

        # 1. Download immagine del cliente
        os.system(f"curl -L {image_url} > source.jpg")

        # 2. Analisi Genere per scelta Voce
        objs = DeepFace.analyze(img_path="source.jpg", actions=['gender'], enforce_detection=False)
        voice = "it-IT-GiuseppeNeural" if objs[0]['dominant_gender'] == "Man" else "it-IT-ElsaNeural"

        # 3. Generazione Audio TTS
        os.system(f'edge-tts --text "{text}" --write-media audio.wav --voice {voice}')

        # 4. Rendering SadTalker
        # Usiamo i parametri che abbiamo testato per la massima qualità
        cmd = (
            f"python inference.py --source_image source.jpg --driven_audio audio.wav "
            f"--result_dir ./results --still --preprocess full --enhancer gfpgan"
        )
        os.system(cmd)

        # 5. Recupero il file video prodotto
        import glob
        files = glob.glob("./results/**/*.mp4", recursive=True)
        if not files:
            return {"status": "error", "message": "Video non generato"}
        
        final_video = max(files, key=os.path.getctime)

        # 6. Caricamento su Cloudflare R2
        video_url = upload_to_r2(final_video, job_id)

        return {
            "status": "completed",
            "video_url": video_url,
            "gender_detected": objs[0]['dominant_gender']
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

runpod.serverless.start({"handler": handler})
