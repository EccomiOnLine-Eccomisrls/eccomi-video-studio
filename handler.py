import os, subprocess, sys, runpod, uuid, glob, time

def install_essentials():
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    libs = ["yacs", "pyyaml", "numpy==1.23.5", "opencv-python-headless==4.8.0.74", "edge-tts", "kornia==0.6.8", "gfpgan", "basicsr==1.4.2", "facexlib", "torchvision==0.13.1", "safetensors", "pydub", "librosa", "resampy", "imageio==2.19.3", "imageio-ffmpeg"]
    for lib in libs: subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir, lib], check=False)
    # Chirurgia Anti-Torchvision
    subprocess.run(f"sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {target_dir}/basicsr/data/degradations.py", shell=True)
    subprocess.run("find . -name '*.py' -exec sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {} +", shell=True)

def upload_video(path):
    # Usiamo Catbox.moe che è il più stabile e il link resta attivo
    try:
        cmd = f"curl -F 'reqtype=fileupload' -F 'fileToUpload=@{path}' https://catbox.moe/user/api.php"
        link = subprocess.check_output(cmd, shell=True).decode().strip()
        if "https://" in link: return link
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
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        # Rendering
        subprocess.run([sys.executable, "inference.py", "--source_image", tmp_img, "--driven_audio", tmp_audio, "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"], env=env, check=True)
        
        video_path = max(glob.glob(f"{tmp_res}/**/*.mp4", recursive=True), key=os.path.getctime)
        link = upload_video(video_path)
        
        if link:
            # QUESTO STAMPA IL LINK NEI LOG CHE VEDI TU
            print(f"\n\n********************************\nLINK VIDEO: {link}\n********************************\n\n", flush=True)
            return {"video_url": link}
        return {"error": "Upload fallito"}
    except Exception as e: return {"error": str(e)}

runpod.serverless.start({"handler": handler})
