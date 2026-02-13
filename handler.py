import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: V78 (Ultra-Force OpenCV & Path Fix)...", flush=True)

def install_essentials():
    print(">>> 1. Pulizia e Installazione in Path Locale...", flush=True)
    # Installiamo tutto in una cartella locale specifica per evitare il conflitto con il sistema
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    
    libs = [
        "numpy==1.23.5", "scikit-image==0.19.3", "imageio==2.9.0", 
        "imageio-ffmpeg", "opencv-python-headless==4.8.0.74", 
        "edge-tts", "safetensors", "kornia==0.6.8", "tqdm", "yacs", 
        "pyyaml", "gfpgan", "facexlib", "librosa", "resampy", 
        "basicsr", "pydub", "scipy==1.10.1"
    ]
    
    # Forziamo l'installazione nella nostra cartella custom
    subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir] + libs, check=True)

    print(">>> 2. CHIRURGIA: Fix Numpy float...", flush=True)
    subprocess.run(f"find . -name '*.py' -exec sed -i 's/np.float/float/g' {{}} +", shell=True)

def handler(job):
    install_essentials()
    
    # Prepariamo l'ambiente per ignorare le librerie di sistema
    custom_env = os.environ.copy()
    custom_env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
    os.makedirs('checkpoints', exist_ok=True)
    # Scarico modelli (omesso per brevità, resta uguale a V77)
    # ... (logica download modelli) ...

    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        
        subprocess.run(["curl", "-k", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> AVVIO RENDERING AI (V78 - Priorità Path Custom)...", flush=True)
        # Lanciamo il processo con il PYTHONPATH modificato
        cmd = [
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=custom_env)
        for line in process.stdout:
            print(f"AI LOG: {line.strip()}", flush=True)
        process.wait()

        # ... (logica upload transfer.sh) ...
        # (Sostituisci con la parte finale solita del codice)
