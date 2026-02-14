import os, subprocess, sys, runpod, uuid, glob, shutil, time

print(">>> CONTAINER AVVIATO: V92 (Triple Delivery Fix)...", flush=True)

def install_essentials():
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    libs = [
        "yacs", "pyyaml", "numpy==1.23.5", "opencv-python-headless==4.8.0.74", 
        "edge-tts", "kornia==0.6.8", "gfpgan", "basicsr==1.4.2", "facexlib", 
        "torchvision==0.13.1", "safetensors", "pydub", "librosa", "resampy", 
        "imageio==2.19.3", "imageio-ffmpeg"
    ]
    for lib in libs:
        subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir, lib], check=False)

    # Chirurgia confermata
    degradations_path = f"{target_dir}/basicsr/data/degradations.py"
    if os.path.exists(degradations_path):
        subprocess.run(f"sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {degradations_path}", shell=True)
    subprocess.run("find . -name '*.py' -exec sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {} +", shell=True)

def upload_video(path, name):
    # Prova 1: BashUpload (molto stabile)
    try:
        print(f">>> Tentativo 1 (BashUpload)...", flush=True)
        out = subprocess.check_output(f"curl -k https://bashupload.com/{name} --upload-file {path}", shell=True).decode()
        if "https://" in out: return out.strip()
    except: pass

    # Prova 2: File.io
    try:
        print(f">>> Tentativo 2 (File.io)...", flush=True)
        out = subprocess.check_output(f"curl -k -F 'file=@{path}' https://file.io", shell=True).decode()
        if '"link":"' in out: return out.split('"link":"')[1].split('"')[0]
    except: pass

    # Prova 3: Transfer.sh (il nostro vecchio amico, come ultima spiaggia)
    try:
        print(f">>> Tentativo 3 (Transfer.sh)...", flush=True)
        return subprocess.check_output(f"curl -k --upload-file {path} https://transfer.sh/{name}", shell=True).decode().strip()
    except: return None

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
        
        print(">>> AVVIO RENDERING (V92)...", flush=True)
        cmd = [sys.executable, "inference.py", "--source_image", tmp_img, "--driven_audio", tmp_audio, "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"]
        subprocess.run(cmd, env=env, check=True)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            link = upload_video(video_path, out_name)
            if link: return {"status": "success", "video_url": link}
            return {"error": "Video creato ma tutti i server di upload sono falliti."}
        
        return {"error": "Rendering finito ma file non trovato."}
    except Exception as e: return {"error": str(e)}

runpod.serverless.start({"handler": handler})
