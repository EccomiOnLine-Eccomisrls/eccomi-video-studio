import os, subprocess, sys, runpod, uuid, glob, shutil, warnings
# Silenziamo gli avvisi di sicurezza (visto che stiamo bypassando l'SSL)
from urllib3.exceptions import InsecureRequestWarning
import boto3
from botocore.config import Config

print(">>> CONTAINER AVVIATO: Inizio v65 (The Nuclear Option)...", flush=True)
warnings.simplefilter('ignore', InsecureRequestWarning)

def install_essentials():
    print(">>> Installazione librerie e Boto3...", flush=True)
    libs = [
        "boto3", "numpy==1.23.5", "imageio==2.9.0", "imageio-ffmpeg", 
        "opencv-python==4.8.0.74", "safetensors", "kornia==0.6.8", 
        "facexlib", "gfpgan", "edge-tts", "scipy==1.10.1", 
        "pydub", "librosa", "resampy", "yacs", "tqdm", "pyyaml"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, check=True, stdout=subprocess.DEVNULL)

def upload_to_r2(file_path, object_name):
    print(f">>> Tentativo Upload Nucleare su R2: {object_name}", flush=True)
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url='https://b8fa6b2877ee48bcac3b22e0665726e1.r2.cloudflarestorage.com',
            aws_access_key_id='006d152c1e6e968032f3088b90c330df',
            aws_secret_access_key='6a2549124d3b9205d83d959b214cc785',
            config=Config(signature_version='s3v4'),
            verify=False # <--- IL TRUCCO: Ignora l'errore SSL
        )
        s3_client.upload_file(file_path, 'eccomionline-video', object_name)
        return f"https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev/{object_name}"
    except Exception as e:
        print(f">>> Errore R2: {e}", flush=True)
        return None

def handler(job):
    install_essentials()
    os.makedirs('checkpoints', exist_ok=True)
    
    # Download modelli AI (usiamo -k per bypassare SSL anche qui)
    urls = ["https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth", 
            "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth", 
            "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"]
    
    for url in urls:
        target = os.path.join('checkpoints', os.path.basename(url))
        if not os.path.exists(target):
            subprocess.run(["curl", "-k", "-L", "-o", target, url])

    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        
        subprocess.run(["curl", "-k", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> Rendering AI in corso...", flush=True)
        subprocess.run([sys.executable, "inference.py", "--source_image", tmp_img, "--driven_audio", tmp_audio, "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"], check=True)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"{uuid.uuid4()}.mp4"
            
            # 1. TENTATIVO R2 (Bypass SSL)
            final_url = upload_to_r2(video_path, out_name)
            
            # 2. PIANO B (Se R2 fallisce, carichiamo su Transfer.sh)
            if not final_url:
                print(">>> R2 Fallito ancora. Uso Piano B (Transfer.sh)...", flush=True)
                upload_b = subprocess.check_output(f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}", shell=True).decode().strip()
                return {"status": "success_via_backup", "video_url": upload_b}
            
            return {"status": "success_r2", "video_url": final_url}
        
        return {"error": "Video non generato."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
