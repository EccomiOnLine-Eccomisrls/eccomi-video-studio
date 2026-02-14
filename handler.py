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
    img_url, text = job['input'].get('image_url'), job['input'].get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"
    try:
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-ElsaNeural", "--write-media", tmp_audio], check=True) # Ho messo Elsa per un tono più naturale
        
        print(">>> AVVIO RENDERING HD (V94)...", flush=True)
        # Comando potenziato: HD, Posa naturale e scala espressioni aumentata
        cmd = [
            sys.executable, "inference.py", 
            "--source_image", tmp_img, 
            "--driven_audio", tmp_audio, 
            "--result_dir", tmp_res, 
            "--still", 
            "--preprocess", "full", 
            "--enhancer", "gfpgan", 
            "--size", "512", 
            "--pose_style", "15",
            "--expression_scale", "1.2"
        ]
        subprocess.run(cmd, env=env, check=True)
        
        video_path = max(glob.glob(f"{tmp_res}/**/*.mp4", recursive=True), key=os.path.getctime)
        link = upload_video(video_path)
        if link:
            print(f"\n********************************\nNUOVO LINK HD: {link}\n********************************\n", flush=True)
            return {"video_url": link}
        return {"error": "Upload fallito"}
    except Exception as e: return {"error": str(e)}

runpod.serverless.start({"handler": handler})
