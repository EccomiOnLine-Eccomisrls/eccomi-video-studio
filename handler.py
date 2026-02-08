import os
import subprocess
import sys
import time

# --- 1. INSTALLAZIONE FORZATA IMMEDIATA ---
# Installiamo subito le librerie che mancano (scipy, resampy, ecc.)
def install_missing_libs():
    critical_libs = ["scipy", "resampy", "numpy==1.23.5", "deepface", "boto3", "edge-tts"]
    for lib in critical_libs:
        subprocess.run([sys.executable, "-m", "pip", "install", lib], check=False)

install_missing_libs()

import runpod
import boto3
import uuid
import glob
import shutil

# --- 2. DOWNLOAD MODELLI ---
def download_models():
    if not os.path.exists('checkpoints'):
        os.makedirs('checkpoints')
    urls = [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]
    for url in urls:
        fn = os.path.join('checkpoints', os.path.basename(url))
        if not os.path.exists(fn):
            subprocess.run(["wget", "-O", fn, url], check=False)

download_models()

# CONFIG R2
R2_CONF = {
    "id": "006d152c1e6e968032f3088b90c330df",
    "key": "6a2549124d3b9205d83d959b214cc785",
    "bucket": "eccomionline-video",
    "endpoint": "https://3320f2693994336c56f7093222830f6a.r2.cloudflarestorage.com",
    "public": "https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev"
}

def handler(job):
    # Importiamo qui per essere sicuri che scipy sia ora disponibile
    from deepface import DeepFace
    import numpy as np
    
    job_input = job['input']
    img_url = job_input.get('image_url')
    text = job_input.get('text')

    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        os.system(f'curl -L -s "{img_url}" -o {tmp_img}')

        # Analisi Genere
        objs = DeepFace.analyze(img_path=tmp_img, actions=['gender'], enforce_detection=False)
        voice = "it-IT-GiuseppeNeural" if objs[0]['dominant_gender'] == "Man" else "it-IT-ElsaNeural"

        # Genera Audio
        os.system(f'edge-tts --text "{text}" --voice {voice} --write-media {tmp_audio}')
        
        # Rendering (Ignoriamo avvisi per non bloccare Numpy)
        env = os.environ.copy()
        env["PYTHONWARNINGS"] = "ignore"
        subprocess.run([
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize"
        ], env=env, check=True)

        # Upload finale
        files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if files:
            out_name = f"{uuid.uuid4()}.mp4"
            s3 = boto3.client('s3', endpoint_url=R2_CONF["endpoint"], aws_access_key_id=R2_CONF["id"], aws_secret_access_key=R2_CONF["key"])
            s3.upload_file(files[0], R2_CONF["bucket"], out_name)
            return {"video_url": f"{R2_CONF['public']}/{out_name}"}
        
        return {"error": "Video non generato."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
