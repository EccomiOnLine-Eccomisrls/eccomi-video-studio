import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: Inizio V76 (Forced OpenCV Purge)...", flush=True)

def install_essentials():
    print(">>> 1. ELIMINAZIONE FISICA OPENCV 4.11...", flush=True)
    # Rimuoviamo forzatamente i file di sistema che causano il crash
    subprocess.run("rm -rf /usr/local/lib/python3.10/dist-packages/cv2*", shell=True)
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "opencv-python", "opencv-python-headless"], check=False)

    print(">>> 2. Installazione Pulita...", flush=True)
    libs = [
        "numpy==1.23.5", "scikit-image==0.19.3", "imageio==2.9.0", 
        "imageio-ffmpeg", "opencv-python-headless==4.8.0.74", 
        "edge-tts", "safetensors", "kornia==0.6.8", "tqdm", "yacs", 
        "pyyaml", "gfpgan", "facexlib", "librosa", "resampy", 
        "basicsr", "pydub", "scipy==1.10.1"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, check=True)

    print(">>> 3. CHIRURGIA: Fix Numpy float...", flush=True)
    subprocess.run("find . -name '*.py' -exec sed -i 's/np.float/float/g' {} +", shell=True)

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
        
        print(">>> AVVIO RENDERING AI (V76 - Clean OpenCV)...", flush=True)
        cmd = [
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
        
        return {"error": "Video non trovato. Controlla i log AI."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
