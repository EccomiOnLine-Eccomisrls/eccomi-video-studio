import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: V86 (Safetensors Fix)...", flush=True)

def install_essentials():
    print(">>> 1. Installazione librerie mancanti...", flush=True)
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    
    # Aggiunti safetensors e dlib che mancavano nella V85
    libs = [
        "numpy==1.23.5", "opencv-python-headless==4.8.0.74", "edge-tts", 
        "kornia==0.6.8", "gfpgan", "basicsr==1.4.2", "facexlib", 
        "torchvision==0.13.1", "scipy==1.10.1", "pydub", "safetensors", "dlib"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir] + libs, check=True)

    print(">>> 2. RE-WRITING: Applicazione fix strutturali...", flush=True)
    # Confermiamo il fix che ha sconfitto Torchvision nella V85
    cmd_fix = "find . -name '*.py' -exec sed -i 's/from torchvision.transforms.functional_tensor import/import torchvision.transforms.functional as/g' {} +"
    subprocess.run(cmd_fix, shell=True)
    subprocess.run("find . -name '*.py' -exec sed -i 's/np.float/float/g' {} +", shell=True)

def handler(job):
    install_essentials()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
    os.makedirs('checkpoints', exist_ok=True)
    
    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-k", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> AVVIO RENDERING (V86)...", flush=True)
        cmd = [sys.executable, "inference.py", "--source_image", tmp_img, "--driven_audio", tmp_audio, "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for line in process.stdout: print(f"AI LOG: {line.strip()}", flush=True)
        process.wait()

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            link = subprocess.check_output(f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}", shell=True).decode().strip()
            return {"status": "success", "video_url": link}
        return {"error": "Rendering completato. Nessun MP4 generato."}
    except Exception as e: return {"error": str(e)}

runpod.serverless.start({"handler": handler})
