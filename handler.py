import os
import subprocess
import sys
import runpod
import uuid
import glob
import requests
import mimetypes
from pathlib import Path

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_VIDEOS_BUCKET", "videos")

def upload_to_supabase(local_path: str, token: str, object_name: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ENV Supabase mancanti (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")
        return None

    p = Path(local_path)
    content_type = mimetypes.guess_type(str(p))[0] or "application/octet-stream"

    object_path = object_name  # es: "{token}.mp4"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{object_path}?upsert=true"

    try:
        file_data = p.read_bytes()
        print(f"📦 File size: {len(file_data)} bytes")
        if len(file_data) < 5000:
            print("❌ File troppo piccolo, blocco upload")
            return None

        headers = {
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "apikey": SUPABASE_KEY,
            "Content-Type": content_type,
        }

        print(f"🚀 Upload Supabase -> bucket={SUPABASE_BUCKET} path={object_path} ({content_type})")
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

def normalize_plan(plan: str) -> str:
    p = (plan or "").strip().lower()
    if p in ["base", "basic"]:
        return "base"
    if p in ["pro"]:
        return "pro"
    if p in ["ultra", "premium"]:
        return "ultra"
    return "base"

def handler(job):
    i = job.get("input", {}) or {}

    token = i.get("token") or str(uuid.uuid4())
    image_url = i.get("image_url")
    text = i.get("text") or ""
    audio_url = i.get("audio_url")
    gender = i.get("gender")
    plan = normalize_plan(i.get("plan", "base"))

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

        # ---- SadTalker args (enhancer solo ULTRA) ----
        cmd = [
            sys.executable,
            "inference.py",
            "--source_image", tmp_image,
            "--driven_audio", tmp_audio,
            "--result_dir", tmp_result,
            "--still",
            "--preprocess", "full",
            "--size", "512"
        ]

        if plan == "ultra":
            cmd += ["--enhancer", "gfpgan"]   # SOLO ULTRA
        # base/pro: niente enhancer

        subprocess.run(cmd, check=True)

        # Trova MP4 generato
        files = glob.glob(f"{tmp_result}/**/*.mp4", recursive=True)
        if not files:
            return {"error": "Nessun video generato (.mp4 non trovato)"}

        video_path = max(files, key=os.path.getctime)
        print("🎬 Video generato:", video_path)

        # Upload su Supabase (ROOT: token.mp4)
        object_name = f"{token}.mp4"
        final_url = upload_to_supabase(video_path, token, object_name)
        if not final_url:
            return {"error": "Upload Supabase fallito"}

        return {
            "video_url": final_url,
            "token": token,
            "plan": plan
        }

    except subprocess.CalledProcessError as e:
        return {"error": f"Subprocess error: {e}"}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
