import os, subprocess, sys, runpod, time, uuid, glob, shutil, urllib3
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

# Disabilitiamo i messaggi di avviso SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print(">>> CONTAINER AVVIATO: Inizio v60 (Forzatura TLS 1.2)...", flush=True)

# Un "adattatore" speciale per forzare il container a usare TLS moderno
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        kwargs['ssl_context'] = context
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

def install_missing_packages():
    libs = [
        "numpy==1.23.5", "imageio==2.9.0", "imageio-ffmpeg", 
        "opencv-python==4.8.0.74", "safetensors", "kornia==0.6.8", 
        "facexlib", "gfpgan", "edge-tts", "scipy==1.10.1", 
        "pydub", "librosa", "resampy", "boto3", "yacs", "tqdm", "pyyaml", "requests-aws4auth"
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-U"] + libs, check=True, stdout=subprocess.DEVNULL)

def handler(job):
    install_missing_packages()
    from requests_aws4auth import AWS4Auth
    
    os.makedirs('checkpoints', exist_ok=True)
    urls = [
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2pose_00140-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/auido2exp_00300-256.pth",
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/facevid2vid_00089-256.pth"
    ]
    for url in urls:
        target = os.path.join('checkpoints', os.path.basename(url))
        if not os.path.exists(target):
            subprocess.run(["wget", "-q", "-O", target, url])

    job_input = job['input']
    img_url, text = job_input.get('image_url'), job_input.get('text')
    tmp_img, tmp_audio, tmp_res = "/tmp/src.jpg", "/tmp/aud.wav", "/tmp/out"

    try:
        if os.path.exists(tmp_res): shutil.rmtree(tmp_res)
        os.makedirs(tmp_res, exist_ok=True)
        subprocess.run(["curl", "-L", "-s", "-o", tmp_img, img_url], check=True)
        subprocess.run(["edge-tts", "--text", text, "--voice", "it-IT-GiuseppeNeural", "--write-media", tmp_audio], check=True)
        
        print(">>> Avvio Rendering AI...", flush=True)
        subprocess.run([
            sys.executable, "inference.py",
            "--source_image", tmp_img, "--driven_audio", tmp_audio,
            "--result_dir", tmp_res, "--still", "--preprocess", "resize", "--enhancer", "gfpgan"
        ], check=True)

        mp4_files = glob.glob(f"{tmp_res}/**/*.mp4", recursive=True)
        if mp4_files:
            video_path = max(mp4_files, key=os.path.getctime)
            out_name = f"{uuid.uuid4()}.mp4"
            
            # Parametri Cloudflare
            access_key = "006d152c1e6e968032f3088b90c330df"
            secret_key = "6a2549124d3b9205d83d959b214cc785"
            endpoint = "https://b8fa6b2877ee48bcac3b22e0665726e1.r2.cloudflarestorage.com"
            bucket = "eccomionline-video"
            
            # Creiamo l'autenticazione S3 per 'requests'
            auth = AWS4Auth(access_key, secret_key, 'us-east-1', 's3')
            upload_url = f"{endpoint}/{bucket}/{out_name}"
            
            print(f">>> Tentativo Upload alternativo: {out_name}", flush=True)
            
            with open(video_path, 'rb') as f:
                s = requests.Session()
                s.mount(endpoint, TLSAdapter()) # Forziamo il TLS moderno
                r = s.put(upload_url, auth=auth, data=f, verify=False)
            
            if r.status_code == 200:
                print(f">>> UPLOAD RIUSCITO CON METODO REQUESTS!", flush=True)
                return {"video_url": f"https://pub-3ca6a3559a564d63bf0900e62cbb23c8.r2.dev/{out_name}"}
            else:
                raise Exception(f"Errore server: {r.status_code} - {r.text}")
        
        return {"error": "Video non generato."}
    except Exception as e:
        print(f">>> ERRORE FINALE: {str(e)}", flush=True)
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
