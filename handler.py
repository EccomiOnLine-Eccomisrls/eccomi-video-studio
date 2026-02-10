import os
import subprocess
import sys
import time

# --- 1. SETUP AMBIENTE COMPLETO (v36) ---
def startup_setup():
    # Aggiunto kornia, yacs e gdown per sicurezza totale
    libs = [
        "numpy==1.23.5", "scipy", "safetensors", "boto3", 
        "deepface", "edge-tts", "opencv-python", "tqdm", 
        "resampy", "scikit-image", "librosa", "kornia==0.6.8",
        "yacs", "gdown"
    ]
    
    print(">>> INSTALLAZIONE DIPENDENZE COMPLETE...")
    for lib in libs:
        subprocess.run([sys.executable, "-m", "pip", "install", lib], check=True)
    
    # --- CURA DEI FILE (Numpy fix) ---
    print(">>> CURA DEI FILE DI SISTEMA...")
    files_to_fix = [
        "src/face3d/util/preprocess.py",
        "inference.py"
    ]
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            fixed_content = content.replace("np.VisibleDeprecationWarning", "Warning")
            with open(file_path, 'w') as f:
                f.write(fixed_content)
            print(f"File curato: {file_path}")

    # Download Modelli
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

startup_setup()

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
    import numpy as np
    
    # Patch per Numpy
    np.float = float
    np.int = int

    job_input = job['input']
    img_url = job_input.get('image_url')
    text = job_input.get('text')

    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        
        subprocess.run(["curl", "-L", "-s", "-o", tmp_img, img_url], check=True)

        # Analisi volto
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

        # Upload Cloudflare
        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            output_filename = f"{uuid.uuid4()}.mp4"
            s3 = boto3.client('s3', endpoint_url=R2_CONF["endpoint"], 
                             aws_access_key_id=R2_CONF["id"], 
                             aws_secret_access_key=R2_CONF["key"])
            s3.upload_file(mp4_files[0], R2_CONF["bucket"], output_filename)
            return {"video_url": f"{R2_CONF['public']}/{output_filename}"}
        
        return {"error": "Video non generato."}

    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
