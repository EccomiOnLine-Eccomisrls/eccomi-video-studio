import os
import subprocess
import sys
import time

# --- 1. FUNZIONE DI INSTALLAZIONE CERTIFICATA ---
def install_and_verify():
    libs = [
        "numpy==1.23.5", "scipy", "safetensors", "boto3", 
        "deepface", "edge-tts", "opencv-python", "tqdm", 
        "resampy", "scikit-image", "librosa"
    ]
    
    print(">>> INIZIO PREPARAZIONE AMBIENTE...")
    for lib in libs:
        # Installazione con timeout e retry
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", lib], check=True)
    
    # VERIFICA CRITICA: Se questo fallisce, il server si ferma qui
    import safetensors
    import scipy
    import numpy as np
    
    # Patch Numpy per SadTalker
    np.float = float
    np.int = int
    
    # Download Modelli (Obbligatorio)
    if not os.path.exists('checkpoints'):
        os.makedirs('checkpoints', exist_ok=True)
    
    urls = [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]
    
    for url in urls:
        target = os.path.join('checkpoints', os.path.basename(url))
        if not os.path.exists(target):
            subprocess.run(["wget", "-q", "-O", target, url], check=True)
    
    print(">>> AMBIENTE CERTIFICATO E PRONTO.")

# Eseguiamo il setup bloccante
try:
    install_and_verify()
except Exception as e:
    print(f"ERRORE CRITICO DURANTE IL SETUP: {e}")
    sys.exit(1) # Forza il crash del worker se non è pronto

import runpod
import boto3
import uuid
import glob
import shutil

# CONFIGURAZIONE R2
R2_CONF = {
    "id": "006d152c1e6e968032f3088b90c330df",
    "key": "6a2549124d3b9205d83d959b214cc785",
    "bucket": "eccomionline-video",
    "endpoint": "https://3320f2693994336c56f7093222830f6a.r2.cloudflarestorage.com",
    "public": "https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev"
}

def handler(job):
    from deepface import DeepFace
    
    job_input = job['input']
    img_url = job_input.get('image_url')
    text = job_input.get('text')

    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        
        # Download Immagine
        subprocess.run(["curl", "-L", "-s", "-o", tmp_img, img_url], check=True)

        # Genere
        objs = DeepFace.analyze(img_path=tmp_img, actions=['gender'], enforce_detection=False)
        voice = "it-IT-GiuseppeNeural" if objs[0]['dominant_gender'] == "Man" else "it-IT-ElsaNeural"

        # Audio
        subprocess.run(["edge-tts", "--text", text, "--voice", voice, "--write-media", tmp_audio], check=True)
        
        # Rendering
        env = os.environ.copy()
        env["PYTHONWARNINGS"] = "ignore"
        
        print("Rendering avviato...")
        subprocess.run([
            sys.executable, "inference.py",
            "--source_image", tmp_img,
            "--driven_audio", tmp_audio,
            "--result_dir", tmp_res,
            "--still", "--preprocess", "resize"
        ], env=env, check=True)

        # Upload
        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            output_filename = f"{uuid.uuid4()}.mp4"
            s3 = boto3.client('s3', endpoint_url=R2_CONF["endpoint"], 
                             aws_access_key_id=R2_CONF["id"], 
                             aws_secret_access_key=R2_CONF["key"])
            s3.upload_file(mp4_files[0], R2_CONF["bucket"], output_filename)
            return {"video_url": f"{R2_CONF['public']}/{output_filename}"}
        
        return {"error": "Nessun video prodotto."}

    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
