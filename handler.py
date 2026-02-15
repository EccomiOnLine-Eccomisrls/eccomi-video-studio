import os, subprocess, sys, runpod, uuid, glob, time

def install_essentials():
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    libs = ["yacs", "pyyaml", "numpy==1.23.5", "opencv-python-headless==4.8.0.74", "edge-tts", "kornia==0.6.8", "gfpgan", "basicsr==1.4.2", "facexlib", "torchvision==0.13.1", "safetensors", "pydub", "librosa", "resampy", "imageio==2.19.3", "imageio-ffmpeg"]
    for lib in libs: subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir, lib], check=False)
    subprocess.run(f"sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {target_dir}/basicsr/data/degradations.py", shell=True)
    subprocess.run("find . -name '*.py' -exec sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {} +", shell=True)

def upload_video(path):
    try:
        cmd = f"curl -F 'reqtype=fileupload' -F 'fileToUpload=@{path}' https://catbox.moe/user/api.php"
        return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return None

def handler(job):
    install_essentials()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
    # --- INPUT DA SHOPIFY/AUTOMAZIONE ---
    img_url = job['input'].get('image_url')
    text = job['input'].get('text')
    user_audio_url = job['input'].get('audio_url') # Link all'audio caricato dall'utente
    gender = job['input'].get('gender', 'male')
    
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"
    try:
        os.makedirs(tmp_res, exist_ok=True)
        # 1. Scarica l'immagine
        subprocess.run(["curl", "-L", "-o", tmp_img, img_url], check=True)
        
        # 2. GESTIONE AUDIO (Priorità al file caricato dall'utente)
        if user_audio_url:
            print(>>> Uso audio caricato dall'utente..., flush=True)
            subprocess.run(["curl", "-L", "-o", tmp_audio, user_audio_url], check=True)
        else:
            print(f">>> Genero voce TTS ({gender})..., flush=True)
            voice = "it-IT-GiuseppeNeural" if gender == "male" else "it-IT-ElsaNeural"
            subprocess.run(["edge-tts", "--text", text, "--voice", voice, "--write-media", tmp_audio], check=True)
        
        # 3. RENDERING HD (Forzato per loghi e persone)
        cmd = [
            sys.executable, "inference.py", 
            "--source_image", tmp_img, 
            "--driven_audio", tmp_audio, 
            "--result_dir", tmp_res, 
            "--still", 
            "--preprocess", "full", # Fondamentale per l'omino!
            "--enhancer", "gfpgan", 
            "--size", "512"
        ]
        subprocess.run(cmd, env=env, check=True)
        
        video_path = max(glob.glob(f"{tmp_res}/**/*.mp4", recursive=True), key=os.path.getctime)
        link = upload_video(video_path)
        return {"video_url": link} if link else {"error": "Upload fallito"}
    except Exception as e: return {"error": str(e)}

runpod.serverless.start({"handler": handler})
