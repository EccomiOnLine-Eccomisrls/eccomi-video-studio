import os, subprocess, sys, runpod, uuid, glob, time

def install_essentials():
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    # Installiamo solo lo stretto necessario per risparmiare minuti preziosi
    libs = ["edge-tts", "gfpgan", "basicsr==1.4.2", "facexlib", "imageio-ffmpeg"]
    for lib in libs: 
        subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir, lib], check=False)
    
    # Patch rapida per torchvision
    subprocess.run(f"find {target_dir} -name 'degradations.py' -exec sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {{}} +", shell=True)

def upload_video(path):
    try:
        return subprocess.check_output(f"curl -F 'reqtype=fileupload' -F 'fileToUpload=@{path}' https://catbox.moe/user/api.php", shell=True).decode().strip()
    except: return None

def handler(job):
    install_essentials()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
    # Dati da Shopify
    i = job['input']
    img, txt, aud, gen = i.get('image_url'), i.get('text'), i.get('audio_url'), i.get('gender', 'male')
    
    tmp_i, tmp_a, tmp_r = "/tmp/s.jpg", "/tmp/a.wav", "/tmp/o"
    try:
        os.makedirs(tmp_r, exist_ok=True)
        subprocess.run(["curl", "-L", "-o", tmp_i, img], check=True)
        
        if aud:
            subprocess.run(["curl", "-L", "-o", tmp_a, aud], check=True)
        else:
            v = "it-IT-GiuseppeNeural" if gen == "male" else "it-IT-ElsaNeural"
            subprocess.run(["edge-tts", "--text", txt, "--voice", v, "--write-media", tmp_a], check=True)
        
        # Rendering HD - Forza riconoscimento volto
        subprocess.run([sys.executable, "inference.py", "--source_image", tmp_i, "--driven_audio", tmp_a, "--result_dir", tmp_r, "--still", "--preprocess", "full", "--enhancer", "gfpgan", "--size", "512"], env=env, check=True)
        
        path = max(glob.glob(f"{tmp_r}/**/*.mp4", recursive=True), key=os.path.getctime)
        url = upload_video(path)
        return {"video_url": url} if url else {"error": "Upload fallito"}
    except Exception as e: return {"error": str(e)}

runpod.serverless.start({"handler": handler})
