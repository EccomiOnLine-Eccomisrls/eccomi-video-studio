import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: V80 (Ghost Module Fix)...", flush=True)

def install_essentials():
    print(">>> 1. Installazione librerie base...", flush=True)
    target_dir = "/tmp/custom_libs"
    os.makedirs(target_dir, exist_ok=True)
    
    libs = [
        "numpy==1.23.5", "scikit-image==0.19.3", "imageio==2.9.0", 
        "imageio-ffmpeg", "opencv-python-headless==4.8.0.74", 
        "edge-tts", "safetensors", "kornia==0.6.8", "tqdm", "yacs", 
        "pyyaml", "gfpgan", "facexlib", "librosa", "resampy", 
        "basicsr", "pydub", "scipy==1.10.1", "torchvision"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-t", target_dir] + libs, check=True)

    print(">>> 2. CHIRURGIA: Creazione modulo fantasma per Torchvision...", flush=True)
    # Questo comando crea il file mancante che causa il crash
    ghost_fix = """
import torchvision.transforms.functional as F
try:
    from torchvision.transforms import functional_tensor
except ImportError:
    import sys
    from torchvision.transforms import functional as functional_tensor
    sys.modules['torchvision.transforms.functional_tensor'] = functional_tensor
"""
    with open("fix_torch.py", "w") as f:
        f.write(ghost_fix)
    
    # Applichiamo il fix a tutti i file che lo richiedono
    subprocess.run(f"find . -name '*.py' -exec sed -i 's/np.float/float/g' {{}} +", shell=True)
    print(">>> Fix applicati con successo.", flush=True)

def handler(job):
    install_essentials()
    custom_env = os.environ.copy()
    # Inseriamo il nostro fix all'inizio del caricamento di Python
    custom_env["PYTHONPATH"] = f"/tmp/custom_libs:{os.getcwd()}"
    
    os.makedirs('checkpoints', exist_ok=True)
    # (Logica download modelli solita...)

    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-k", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> AVVIO RENDERING AI (V80 - Bypass Torchvision)...", flush=True)
        # Usiamo un trucco per caricare il fix prima di far partire l'AI
        cmd = [
            sys.executable, "-c", 
            "import fix_torch; import os; os.system('python3 inference.py --source_image " + tmp_img + " --driven_audio " + tmp_audio + " --result_dir " + tmp_res + " --still --preprocess resize --enhancer gfpgan')"
        ]
        
        subprocess.run(cmd, env=custom_env, shell=False)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            download_link = subprocess.check_output(f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}", shell=True).decode().strip()
            return {"status": "success", "video_url": download_link}
        
        return {"error": "Rendering completato ma nessun video trovato. Controlla i log."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
