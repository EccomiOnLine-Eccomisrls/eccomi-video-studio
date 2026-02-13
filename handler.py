import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: V79 (Torch & Path Alignment)...", flush=True)

def install_essentials():
    print(">>> 1. Pulizia e Installazione Ambiente Completo...", flush=True)
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    
    # Abbiamo aggiunto torch e torchvision specifiche per evitare il ModuleNotFoundError
    libs = [
        "torch==1.12.1+cu113", 
        "torchvision==0.13.1+cu113",
        "numpy==1.23.5", "scikit-image==0.19.3", "imageio==2.9.0", 
        "imageio-ffmpeg", "opencv-python-headless==4.8.0.74", 
        "edge-tts", "safetensors", "kornia==0.6.8", "tqdm", "yacs", 
        "pyyaml", "gfpgan", "facexlib", "librosa", "resampy", 
        "basicsr", "pydub", "scipy==1.10.1"
    ]
    
    # Usiamo un URL specifico per le versioni CUDA di Torch
    subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir, "--extra-index-url", "https://download.pytorch.org/whl/cu113"] + libs, check=True)

    print(">>> 2. CHIRURGIA: Fix finali nel codice...", flush=True)
    subprocess.run(f"find . -name '*.py' -exec sed -i 's/np.float/float/g' {{}} +", shell=True)

def handler(job):
    install_essentials()
    
    # Importante: impostiamo il PYTHONPATH prima di tutto il resto
    custom_env = os.environ.copy()
    custom_env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
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
        
        print(">>> AVVIO RENDERING AI (V79 - Full Compatibility)...", flush=True)
        cmd = [
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=custom_env)
        for line in process.stdout:
            print(f"AI LOG: {line.strip()}", flush=True)
        process.wait()

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            download_link = subprocess.check_output(f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}", shell=True).decode().strip()
            return {"status": "success", "video_url": download_link}
        
        return {"error": "Il rendering è terminato senza produrre un file mp4."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
