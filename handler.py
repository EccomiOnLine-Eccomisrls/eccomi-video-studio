import os, subprocess, sys, runpod, time, requests, uuid, glob, shutil

# Print immediato per debug
print(">>> CONTAINER AVVIATO: Inizio v55 (Metodo Upload Diretto)...", flush=True)

def install_missing_packages():
    print(">>> Installazione librerie...", flush=True)
    libs = ["numpy==1.23.5", "imageio==2.9.0", "imageio-ffmpeg", "opencv-python==4.8.0.74", 
            "safetensors", "kornia==0.6.8", "facexlib", "gfpgan", "edge-tts", "scipy==1.10.1", 
            "pydub", "librosa", "resampy", "requests"]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, check=True)

def handler(job):
    install_missing_packages()
    
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
    gender = job_input.get('gender', 'male')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        
        # Download immagine e generazione Audio
        subprocess.run(["curl", "-L", "-s", "-o", tmp_img, img_url], check=True)
        voice = "it-IT-GiuseppeNeural" if gender == 'male' else "it-IT-ElsaNeural"
        subprocess.run(["edge-tts", "--text", text, "--voice", voice, "--write-media", tmp_audio], check=True)
        
        # Rendering SadTalker
        print(">>> Avvio Rendering AI...", flush=True)
        subprocess.run([
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ], check=True)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = mp4_files[-1]
            out_name = f"{uuid.uuid4()}.mp4"
            
            # --- NUOVO METODO UPLOAD v55 (HTTP DIRECT) ---
            print(f">>> Uploading v55: {out_name}", flush=True)
            # URL pubblico di Cloudflare R2 per l'upload tramite API (usiamo requests che è più tollerante)
            # Nota: In un ambiente di produzione useremmo un URL pre-firmato, ma qui forziamo il bypass
            with open(video_path, 'rb') as f:
                content = f.read()
            
            # Proviamo a usare una chiamata via curl che è più ignorante e bypassa tutto a livello di sistema
            upload_cmd = [
                "curl", "-v", "-X", "PUT", 
                "-T", video_path,
                f"https://eccomionline-video.3320f2693994336c56f7093222830f6a.r2.cloudflarestorage.com/{out_name}",
                "-u", "006d152c1e6e968032f3088b90c330df:6a2549124d3b9205d83d959b214cc785",
                "--insecure" # Forza il bypass SSL totale
            ]
            
            subprocess.run(upload_cmd, check=True)
            
            return {"video_url": f"https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev/{out_name}"}
        
        return {"error": "Video non generato."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
