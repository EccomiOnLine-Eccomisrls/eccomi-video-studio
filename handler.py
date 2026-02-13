import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: V84 (Runtime Override)...", flush=True)

def install_essentials():
    print(">>> 1. Installazione librerie...", flush=True)
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    
    # Installiamo una versione specifica di kornia che spesso risolve questi conflitti
    libs = [
        "numpy==1.23.5", "scikit-image==0.19.3", "opencv-python-headless==4.8.0.74", 
        "edge-tts", "safetensors", "kornia==0.6.8", "tqdm", "yacs", "gfpgan", 
        "facexlib", "librosa", "resampy", "basicsr", "pydub", "scipy==1.10.1", "torchvision"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir] + libs, check=True)

def handler(job):
    install_essentials()
    custom_env = os.environ.copy()
    custom_env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
    # Scarichiamo i modelli se mancano
    os.makedirs('checkpoints', exist_ok=True)
    
    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-k", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> AVVIO RENDERING (V84 - Force Bypass)...", flush=True)
        
        # TRUCCO FINALE: Iniettiamo il fix DIRETTAMENTE nel comando di esecuzione
        # Invece di 'python3 inference.py', eseguiamo un comando che prima corregge Torch e poi lancia il rendering
        cmd = [
            sys.executable, "-c", 
            "import sys; import torchvision; import torchvision.transforms.functional as F; sys.modules['torchvision.transforms.functional_tensor'] = F; " +
            "import os; os.system('python3 inference.py --source_image " + tmp_img + " --driven_audio " + tmp_audio + " --result_dir " + tmp_res + " --still --preprocess resize --enhancer gfpgan')"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=custom_env)
        for line in process.stdout:
            print(f"AI LOG: {line.strip()}", flush=True)
        process.wait()

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            link = subprocess.check_output(f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}", shell=True).decode().strip()
            return {"status": "success", "video_url": link}
        return {"error": "Rendering completato senza MP4. Controlla i log."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
