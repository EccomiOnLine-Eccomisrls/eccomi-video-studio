import os, subprocess, sys, runpod, time, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: Inizio v64 (Fix Unzip + RClone)...", flush=True)

def install_essentials():
    print(">>> Aggiornamento sistema e installazione 'unzip'...", flush=True)
    try:
        # 1. Installiamo 'unzip' che manca nel container
        subprocess.run("apt-get update && apt-get install -y unzip", shell=True, check=True)
        
        # 2. Ora installiamo RClone
        print(">>> Installazione RClone...", flush=True)
        subprocess.run("curl https://rclone.org/install.sh | bash", shell=True, check=True)
    except Exception as e:
        print(f">>> ERRORE installazione sistema: {e}", flush=True)

    print(">>> Installazione librerie Python...", flush=True)
    libs = [
        "numpy==1.23.5", "imageio==2.9.0", "imageio-ffmpeg", 
        "opencv-python==4.8.0.74", "safetensors", "kornia==0.6.8", 
        "facexlib", "gfpgan", "edge-tts", "scipy==1.10.1", 
        "pydub", "librosa", "resampy", "yacs", "tqdm", "pyyaml"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, check=True, stdout=subprocess.DEVNULL)

def configure_rclone():
    conf = f"""
[r2]
type = s3
provider = Cloudflare
access_key_id = 006d152c1e6e968032f3088b90c330df
secret_access_key = 6a2549124d3b9205d83d959b214cc785
endpoint = https://b8fa6b2877ee48bcac3b22e0665726e1.r2.cloudflarestorage.com
acl = public-read
"""
    rclone_path = os.path.expanduser("~/.config/rclone")
    os.makedirs(rclone_path, exist_ok=True)
    with open(os.path.join(rclone_path, "rclone.conf"), "w") as f:
        f.write(conf)

def handler(job):
    install_essentials()
    configure_rclone()
    
    # Pre-caricamento modelli AI
    os.makedirs('checkpoints', exist_ok=True)
    urls = [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]
    for url in urls:
        target = os.path.join('checkpoints', os.path.basename(url))
        if not os.path.exists(target):
            subprocess.run(["wget", "-q", "-O", target, url])

    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        
        subprocess.run(["curl", "-L", "-s", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> Avvio Rendering AI...", flush=True)
        subprocess.run([
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ], check=True)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"{uuid.uuid4()}.mp4"
            
            print(f">>> Caricamento con RClone: {out_name}", flush=True)
            # Usiamo --no-check-certificate come paracadute finale
            subprocess.run(["rclone", "copyto", video_path, f"r2:eccomionline-video/{out_name}", "--no-check-certificate"], check=True)
            
            return {"video_url": f"https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev/{out_name}"}
        
        return {"error": "Video non generato."}
    except Exception as e:
        print(f">>> ERRORE FINALE: {str(e)}", flush=True)
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
