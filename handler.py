import os, subprocess, sys, runpod, uuid, glob, shutil, time

print(">>> CONTAINER AVVIATO: V91 (The Victory Lap)...", flush=True)

def install_essentials():
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    
    # Aggiunto imageio-ffmpeg per risolvere l'errore TiffWriter
    libs = [
        "yacs", "pyyaml", "numpy==1.23.5", "opencv-python-headless==4.8.0.74", 
        "edge-tts", "kornia==0.6.8", "gfpgan", "basicsr==1.4.2", "facexlib", 
        "torchvision==0.13.1", "safetensors", "pydub", "librosa", "resampy", 
        "imageio==2.19.3", "imageio-ffmpeg"
    ]
    
    for lib in libs:
        subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir, lib], check=False)

    print(">>> Esecuzione Chirurgia (confermata funzionante)...", flush=True)
    degradations_path = f"{target_dir}/basicsr/data/degradations.py"
    if os.path.exists(degradations_path):
        subprocess.run(f"sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {degradations_path}", shell=True)
    subprocess.run("find . -name '*.py' -exec sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {} +", shell=True)

def handler(job):
    install_essentials()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-k", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> AVVIO RENDERING FINALE (V91)...", flush=True)
        cmd = [sys.executable, "inference.py", "--source_image", tmp_img, "--driven_audio", tmp_audio, "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for line in process.stdout: print(f"AI LOG: {line.strip()}", flush=True)
        process.wait()

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            
            # Tentativo di upload con retry
            for i in range(3):
                try:
                    link = subprocess.check_output(f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}", shell=True).decode().strip()
                    if "transfer.sh" in link: return {"status": "success", "video_url": link}
                except: time.sleep(2)
            
            return {"status": "partial_success", "message": "Video creato ma upload fallito.", "local_path": video_path}
        
        return {"error": "Rendering finito ma file non trovato. Controlla i log di imageio."}
    except Exception as e: return {"error": str(e)}

runpod.serverless.start({"handler": handler})
