import os
import subprocess
import sys
import runpod
import uuid
import glob
import requests

# --- CONFIG SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_VIDEOS_BUCKET", "videos")

def upload_to_supabase(local_path, token):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ENV Supabase mancanti!")
        return None

    object_path = f"evs/{token}.mp4"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{object_path}"

    try:
        with open(local_path, "rb") as f:
            file_data = f.read()

        if len(file_data) < 5000:
            print("❌ File troppo piccolo")
            return None

        headers = {
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "video/mp4",
            "x-upsert": "true"
        }

        print(f"🚀 Upload Supabase: {object_path}")
        r = requests.post(upload_url, headers=headers, data=file_data, timeout=300)

        if r.status_code in [200, 201]:
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{object_path}"
            print("✅ Upload OK:", public_url)
            return public_url
        else:
            print("❌ Errore Supabase:", r.text)
            return None

    except Exception as e:
        print("❌ Eccezione upload:", e)
        return None


def handler(job):
    i = job["input"]

    token = i.get("token") or str(uuid.uuid4())
    image_url = i.get("image_url")
    text = i.get("text")
    audio_url = i.get("audio_url")
    gender = i.get("gender", "male")

    tmp_image = "/tmp/source.jpg"
    tmp_audio = "/tmp/audio.wav"
    tmp_result = "/tmp/results"

    try:
        os.makedirs(tmp_result, exist_ok=True)

        # Scarica immagine
        subprocess.run(["curl", "-L", "-o", tmp_image, image_url], check=True)

        # Audio
        if audio_url:
            subprocess.run(["curl", "-L", "-o", tmp_audio, audio_url], check=True)
        else:
            voice = "it-IT-GiuseppeNeural" if gender == "male" else "it-IT-ElsaNeural"
            subprocess.run([
                "edge-tts",
                "--text", text,
                "--voice", voice,
                "--write-media", tmp_audio
            ], check=True)

        # Inference SadTalker
        subprocess.run([
            sys.executable,
            "inference.py",
            "--source_image", tmp_image,
            "--driven_audio", tmp_audio,
            "--result_dir", tmp_result,
            "--still",
            "--preprocess", "full",
            "--enhancer", "gfpgan",
            "--size", "512"
        ], check=True)

        # Trova MP4 generato
        files = glob.glob(f"{tmp_result}/**/*.mp4", recursive=True)
        if not files:
            return {"error": "Nessun video generato"}

        video_path = max(files, key=os.path.getctime)

        # Upload diretto Supabase
        final_url = upload_to_supabase(video_path, token)

        if not final_url:
            return {"error": "Upload Supabase fallito"}

        return {
            "status": "completed",
            "video_url": final_url,
            "token": token
        }

    except Exception as e:
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
