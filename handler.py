import os, subprocess, sys, runpod, uuid, glob, shutil

print(">>> CONTAINER AVVIATO: Inizio V67 (Transfer.sh - Link Diretto)...", flush=True)

def install_essentials():
    print(">>> Installazione librerie AI...", flush=True)
    libs = ["numpy==1.23.5", "imageio==2.9.0", "imageio-ffmpeg", "opencv-python==4.8.0.74", "edge-tts"]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, check=True, stdout=subprocess.DEVNULL)

def handler(job):
    install_essentials()
    
    # Download modelli AI bypassando i certificati rotto del container
    os.makedirs('checkpoints', exist_ok=True)
    for model_url in [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]:
        target = os.path.join('checkpoints', os.path.basename(model_url))
        if not os.path.exists(target):
            subprocess.run(["curl", "-k", "-L", "-o", target, model_url])

    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        
        # Download risorse
        subprocess.run(["curl", "-k", "-L", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> Avvio Rendering AI (SadTalker)...", flush=True)
        subprocess.run([
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ], check=True)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
            
            print(f">>> Caricamento su Transfer.sh in corso...", flush=True)
            # Il comando magico: carichiamo e catturiamo il link di risposta
            # Usiamo -k per ignorare eventuali problemi SSL anche qui
            upload_cmd = f"curl -k --upload-file {video_path} https://transfer.sh/{out_name}"
            download_link = subprocess.check_output(upload_cmd, shell=True).decode().strip()
            
            print(f">>> SUCCESSO! Link creato: {download_link}", flush=True)
            return {
                "status": "success",
                "video_url": download_link
            }
        
        return {"error": "Video non generato."}
    except Exception as e:
        print(f">>> ERRORE: {str(e)}", flush=True)
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})

