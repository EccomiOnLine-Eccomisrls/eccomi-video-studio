import os, subprocess, sys, runpod

def install_missing_packages():
    print(">>> FASE 1: Pulizia profonda e allineamento...")
    # Rimuoviamo versioni conflittuali
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "numpy", "protobuf", "tensorflow", "tensorboard"], stdout=subprocess.DEVNULL)
    
    # Installiamo le versioni "sacre" per SadTalker
    print(">>> FASE 2: Installazione pacchetti core...")
    libs = [
        "numpy==1.23.5", "protobuf==3.20.3", "scipy", "safetensors", 
        "boto3", "edge-tts", "opencv-python", "tqdm", "resampy", 
        "scikit-image", "librosa", "kornia==0.6.8", "yacs", "gdown", 
        "facexlib", "gfpgan", "deepface"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, stdout=subprocess.DEVNULL)
    
    # Patch per l'errore 'numpy has no attribute dtypes'
    try:
        import numpy as np
        if not hasattr(np, 'dtypes'):
            class Dtypes: pass
            np.dtypes = Dtypes()
    except: pass

    # Fix file SadTalker
    for f in ["src/face3d/util/preprocess.py", "inference.py"]:
        if os.path.exists(f):
            os.system(f"sed -i 's/np.VisibleDeprecationWarning/Warning/g' {f}")
    print(">>> Ambiente v42 PRONTO.")

def handler(job):
    install_missing_packages()
    
    import boto3, uuid, glob, shutil
    from deepface import DeepFace
    import numpy as np
    
    # Patch compatibilità
    np.float = float
    np.int = int

    # Modelli
    os.makedirs('checkpoints', exist_ok=True)
    urls = [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]
    for url in urls:
        target = os.path.join('checkpoints', os.path.basename(url))
        if not os.path.exists(target):
            os.system(f"wget -q -O {target} {url}")

    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-L", "-s", "-o", tmp_img, img_url], check=True)

        # Analisi genere e voce
        objs = DeepFace.analyze(img_path=tmp_img, actions=['gender'], enforce_detection=False)
        voice = "it-IT-GiuseppeNeural" if objs[0]['dominant_gender'] == "Man" else "it-IT-ElsaNeural"
        subprocess.run(["edge-tts", "--text", text, "--voice", voice, "--write-media", tmp_audio], check=True)
        
        print(">>> Rendering video v42...")
        env = os.environ.copy()
        env["PYTHONWARNINGS"] = "ignore"
        subprocess.run([
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize"
        ], env=env, check=True)

        # Upload R2
        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            out_name = f"{uuid.uuid4()}.mp4"
            r2 = boto3.client('s3', endpoint_url="https://3320f2693994336c56f7093222830f6a.r2.cloudflarestorage.com", 
                              aws_access_key_id="006d152c1e6e968032f3088b90c330df", 
                              aws_secret_access_key="6a2549124d3b9205d83d959b214cc785")
            r2.upload_file(mp4_files[0], "eccomionline-video", out_name)
            return {"video_url": f"https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev/{out_name}"}
        return {"error": "Generazione fallita."}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
