import os
import subprocess
import sys
import runpod
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

def install_and_download():
    # 1. Installazione Librerie
    reqs = ["safetensors", "boto3", "deepface", "edge-tts", "scipy", "numpy==1.23.5", "scikit-image", "opencv-python", "tqdm", "librosa"]
    for req in reqs:
        subprocess.run([sys.executable, "-m", "pip", "install", req], check=False)

    # 2. Creazione cartella modelli e download file .pth mancanti
    if not os.path.exists('checkpoints'):
        os.makedirs('checkpoints')
    
    urls = [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]
    
    for url in urls:
        filename = os.path.join('checkpoints', os.path.basename(url))
        if not os.path.exists(filename):
            print(f"Scaricamento modello: {filename}...")
            subprocess.run(["wget", "-O", filename, url])

# Eseguiamo il setup all'avvio del container
install_and_download()

def handler(job):
    from deepface import DeepFace
    
    job_input = job['input']
    image_url = job_input.get('image_url')
    text = job_input.get('text')

    source_path = "/tmp/source.jpg"
    audio_path = "/tmp/audio.wav"
    results_dir = "/tmp/results"

    try:
        if os.path.exists(results_dir): shutil.rmtree(results_dir)
        os.makedirs(results_dir, exist_ok=True)

        # 1. DOWNLOAD FOTO
        os.system(f'curl -L -s -f "{image_url}" -o {source_path}')
        time.sleep(2)

        if not os.path.exists(source_path):
            return {"error": "Foto non scaricata. Controlla il link."}

        # 2. ANALISI E VOCE
        objs = DeepFace.analyze(img_path=source_path, actions=['gender'], enforce_detection=False)
        voice = "it-IT-GiuseppeNeural" if objs[0]['dominant_gender'] == "Man" else "it-IT-ElsaNeural"

        # 3. GENERAZIONE AUDIO
        os.system(f'edge-tts --text "{text}" --voice {voice} --write-media {audio_path}')
        
        # 4. RENDERING (Ora i file in /checkpoints ci sono!)
        os.system(f"python inference.py --source_image {source_path} --driven_audio {audio_path} --result_dir {results_dir} --still --preprocess resize")

        # 5. INVIO A CLOUDFLARE
        mp4_files = glob.glob(f"{results_dir}/**/*.mp4", recursive=True)
        if mp4_files:
            output_filename = f"{uuid.uuid4()}.mp4"
            s3 = boto3.client('s3', endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY)
            s3.upload_file(mp4_files[0], R2_BUCKET_NAME, output_filename)
            return {"video_url": f"{R2_PUBLIC_URL}/{output_filename}"}
        
        return {"error": "Il video non è stato generato. Controlla i Log di sistema."}

    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
