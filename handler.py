import os
import subprocess
import sys
import runpod
import uuid
import glob
import requests
import mimetypes
from pathlib import Path

# --- CONFIG SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
# usa Service Role (consigliato per upload server-side)
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_VIDEOS_BUCKET", "videos")

def upload_to_supabase(local_path: str, token: str):
    """
    Upload su Supabase Storage via REST API.
    Endpoint corretto: /storage/v1/object/{bucket}/{path}?upsert=true
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ENV Supabase mancanti (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")
        return None

    p = Path(local_path)
    ext = p.suffix.lower() or ".mp4"
    object_path = f"evs/{token}{ext}"

    # ✅ ENDPOINT CORRETTO (NOTA: niente /upload/)
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{object_path}?upsert=true"

    content_type = mimetypes.guess_type(str(p))[0] or "application/octet-stream"

    try:
        file_data = p.read_bytes()
        print(f"📦 File size: {len(file_data)} bytes")

        if len(file_data) < 5000:
            print("❌ File troppo piccolo, blocco upload")
            return None

        headers = {
            # Supabase accetta sia Authorization Bearer sia apikey
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "apikey": SUPABASE_KEY,
            "Content-Type": content_type,
        }

        print(f"🚀 Upload Supabase -> bucket={SUPABASE_BUCKET} path={object_path} ({content_type})")
        # Supabase supporta PUT per upload oggetti
        r = requests.put(upload_url, headers=headers, data=file_data, timeout=300)

        if r.status_code in (200, 201):
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{object_path}"
            print("✅ Upload OK:", public_url)
            return public_url

        print("❌ Upload KO:", r.status_code, r.text)
        return None

    except Exception as e:
        print("❌ Eccezione upload:", repr(e))
        return None


def handler(job):
    i = job.get("input", {})

    token = i.get("token") or str(uuid.uuid4())
    image_url = i.get("image_url")
    text = i.get("text") or ""
    audio_url = i.get("audio_url")
    gender = i.get("gender")  # nessun default

    if not image_url:
        return {"error": "image_url mancante"}

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
           if not text:
              return {"error": "Testo mancante per generazione TTS"}

           if not gender:
              return {"error": "Gender mancante per generazione TTS"}

           if gender == "male":
              voice = "it-IT-GiuseppeNeural"
           elif gender == "female":
              voice = "it-IT-ElsaNeural"
           else:
              return {"error": "Gender non valido"}

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
            return {"error": "Nessun video generato (.mp4 non trovato)"}

        video_path = max(files, key=os.path.getctime)
        print("🎬 Video generato:", video_path)

        # Upload Supabase
        final_url = upload_to_supabase(video_path, token)
        if not final_url:
            return {"error": "Upload Supabase fallito"}

        # ✅ output chiaro per Render (poll_runpod)
        return {
            "status": "completed",
            "video_url": final_url,
            "token": token
        }

    except subprocess.CalledProcessError as e:
        return {"error": f"Subprocess error: {e}"}
    except Exception as e:
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
