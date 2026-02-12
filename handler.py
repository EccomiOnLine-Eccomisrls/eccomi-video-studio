import os, subprocess, sys, runpod, time, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: Inizio v63 (Metodo RClone - No SSL Errors)...", flush=True)

def install_and_configure_rclone():
    # Installiamo rclone (il bulldozer dei caricamenti cloud)
    subprocess.run("curl https://rclone.org/install.sh | bash", shell=True, check=True)
    
    # Configurazione rapida per il tuo Cloudflare R2
    conf = f"""
[r2]
type = s3
provider = Cloudflare
access_key_id = 006d152c1e6e968032f3088b90c330df
secret_access_key = 6a2549124d3b9205d83d959b214cc785
endpoint = https://b8fa6b2877ee48bcac3b22e0665726e1.r2.cloudflarestorage.com
"""
    os.makedirs(os.path.expanduser("~/.config/rclone"), exist_ok=True)
    with open(os.path.expanduser("~/.config/rclone/rclone.conf"), "w") as f:
        f.write(conf)

def install_python_libs():
    libs = ["numpy==1.23.5", "imageio==2.9.0", "imageio-ffmpeg", "opencv-python==4.8.0.74", "safetensors", "kornia==0.6.8", "facexlib", "gfpgan", "edge-tts", "scipy==1.10.1", "pydub", "librosa", "resampy", "yacs", "tqdm", "pyyaml"]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, check=True, stdout=subprocess.DEVNULL)

def handler(job):
    install_and_configure_rclone()
    install_python_libs()
    
    # ... (Codice di rendering identico a prima) ...
    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"
    
    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-L", "-s", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> Rendering AI in corso...", flush=True)
        subprocess.run([sys.executable, "inference.py", "--source_image", tmp_img, "--driven_audio", tmp_audio, "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"], check=True)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"{uuid.uuid4()}.mp4"
            
            print(f">>> Uploading via RClone: {out_name}...", flush=True)
            # USIAMO RCLONE: addio errori SSL di Python!
            subprocess.run(["rclone", "copyto", video_path, f"r2:eccomionline-video/{out_name}", "--no-check-certificate"], check=True)
            
            print(f">>> TRAGUARDO RAGGIUNTO!", flush=True)
            return {"video_url": f"https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev/{out_name}"}
            
    except Exception as e:
        print(f">>> ERRORE: {str(e)}", flush=True)
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
