import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: Inizio V72 (Force OpenCV 4.8 Fix)...", flush=True)

def install_essentials():
    print(">>> 1. Pulizia Totale OpenCV...", flush=True)
    # Rimuoviamo ogni possibile versione di OpenCV installata
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "opencv-python", "opencv-contrib-python", "opencv-python-headless"], check=False)
    
    print(">>> 2. Installazione Blindata (Versioni Certificate)...", flush=True)
    libs = [
        "numpy==1.23.5", 
        "scikit-image==0.19.3",
        "opencv-python-headless==4.8.0.74", # <--- QUESTA DEVE VINCERE
        "imageio==2.9.0", 
        "imageio-ffmpeg", 
        "edge-tts", "safetensors", "kornia==0.6.8", "tqdm", "yacs", 
        "pyyaml", "gfpgan", "facexlib", "librosa", "resampy", 
        "basicsr", "pydub", "scipy==1.10.1"
    ]
    # Installiamo uno per uno per essere sicuri che nessuno fallisca silenziosamente
    for lib in libs:
        subprocess.run([sys.executable, "-m", "pip", "install", lib], check=True)

def handler(job):
    install_essentials()
    
    os.makedirs('checkpoints', exist_ok=True)
    models = [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]
    for url in models:
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
        
        print(">>> AVVIO RENDERING AI (V72 - Forza Bruta)...", flush=True)
        # Usiamo PYTHONPATH=. per essere sicuri che veda i moduli locali
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        
        cmd = [
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for line in process.stdout:
            print(f"AI LOG: {line.strip()}", flush=True)
        process.wait()

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            
            print(f">>> Caricamento su Transfer.sh...", flush=True)
            upload_cmd = f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}"
            download_link = subprocess.check_output(upload_cmd, shell=True).decode().strip()
            
            return {"status": "success", "video_url": download_link}
        
        return {"error": "Il rendering si è fermato. Guarda i log sopra per l'errore di OpenCV."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
