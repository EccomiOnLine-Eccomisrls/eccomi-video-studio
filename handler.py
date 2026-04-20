import os
import subprocess
import sys
import runpod
import uuid
import glob
import requests
import mimetypes
import time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_VIDEOS_BUCKET", "videos")
SUPABASE_TABLE = os.getenv("SUPABASE_VIDEO_JOBS_TABLE", "video_jobs")


def upload_to_supabase(local_path: str, token: str, object_name: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ENV Supabase mancanti (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")
        return None

    p = Path(local_path)
    content_type = mimetypes.guess_type(str(p))[0] or "application/octet-stream"

    object_path = object_name
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


def patch_video_job(token: str, payload: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ ENV Supabase mancanti: skip patch video_jobs")
        return False

    if not token:
        print("⚠️ token mancante: skip patch video_jobs")
        return False

    patch_url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?evs_token=eq.{quote(str(token), safe='')}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    r = requests.patch(patch_url, headers=headers, json=payload, timeout=60)
    print("📬 PATCH video_jobs:", r.status_code, r.text[:500])
    r.raise_for_status()
    return True


def mark_video_job_done(token: str, final_url: str, reel_url: str = None, processing_seconds: int = None):
    now_iso = datetime.now(timezone.utc).isoformat()

    public_watch_url = f"https://video.eccomionline.com/video/{token}"

    payload = {
        "status": "done",
        "video_url": public_watch_url,
        "video_supabase_url": final_url,
        "video_reel_url": reel_url,
        "video_url_source": "supabase",
        "finished_at": now_iso,
        "updated_at": now_iso,
    }

    if processing_seconds is not None:
        payload["processing_seconds"] = int(processing_seconds)

    return patch_video_job(token, payload)


def mark_video_job_failed(token: str, error_message: str):
    now_iso = datetime.now(timezone.utc).isoformat()

    payload = {
        "status": "failed",
        "finished_at": now_iso,
        "updated_at": now_iso,
    }

    ok = patch_video_job(token, payload)
    print("❌ video_jobs segnato failed:", ok, "| error:", error_message)
    return ok


def normalize_plan(plan: str) -> str:
    p = (plan or "").strip().lower()
    if p in ["base", "basic"]:
        return "base"
    if p in ["pro"]:
        return "pro"
    if p in ["ultra", "premium"]:
        return "ultra"
    return "base"

def pick_tts_profile(voice_profile: str, gender: str):
    vp = (voice_profile or "").strip().lower()

    profiles = {
        "man_standard":   {"voice": "it-IT-GiuseppeNeural", "rate": "+0%",  "pitch": "+0Hz"},
        "man_happy":      {"voice": "it-IT-GiuseppeNeural", "rate": "+10%", "pitch": "+2Hz"},
        "man_serious":    {"voice": "it-IT-GiuseppeNeural", "rate": "-10%", "pitch": "-2Hz"},

        "woman_standard": {"voice": "it-IT-ElsaNeural",     "rate": "+0%",  "pitch": "+0Hz"},
        "woman_happy":    {"voice": "it-IT-ElsaNeural",     "rate": "+10%", "pitch": "+2Hz"},
        "woman_serious":  {"voice": "it-IT-ElsaNeural",     "rate": "-10%", "pitch": "-2Hz"},

        "boy":            {"voice": "it-IT-GiuseppeNeural", "rate": "+18%", "pitch": "+6Hz"},
        "girl":           {"voice": "it-IT-ElsaNeural",     "rate": "+18%", "pitch": "+6Hz"},
    }

    if vp in profiles:
        return profiles[vp]

    if (gender or "").lower() in ["female", "f", "donna", "femmina"]:
        return {"voice": "it-IT-ElsaNeural", "rate": "+0%", "pitch": "+0Hz"}

    return {"voice": "it-IT-GiuseppeNeural", "rate": "+0%", "pitch": "+0Hz"}


def create_reel_ffmpeg(input_mp4: str, output_mp4: str):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_mp4,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_mp4
    ]
    subprocess.run(cmd, check=True)


def polish_video_ffmpeg(input_mp4: str, output_mp4: str):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_mp4,
        "-vf", "unsharp=5:5:0.4:5:5:0.0,eq=contrast=1.03:brightness=0.01:saturation=1.03",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_mp4
    ]
    subprocess.run(cmd, check=True)


def handler(job):
    start_ts = time.time()
    i = job.get("input", {}) or {}

    token = i.get("token") or i.get("evs_token") or str(uuid.uuid4())
    image_url = i.get("image_url")
    text = i.get("text") or ""
    audio_url = i.get("audio_url")

    voice_profile = i.get("voice_profile") or ""
    gender = (i.get("gender") or "").lower()

    tts_profile = pick_tts_profile(voice_profile, gender)
    voice = tts_profile["voice"]
    rate = tts_profile["rate"]
    pitch = tts_profile["pitch"]

    print("TOKEN:", token)
    print("GENDER:", gender)
    print("VOICE_PROFILE:", voice_profile)
    print("VOICE:", voice)
    print("RATE:", rate)
    print("PITCH:", pitch)

    plan = normalize_plan(i.get("plan", "base"))

    tmp_image = "/tmp/source.jpg"
    tmp_audio = "/tmp/audio.wav"
    tmp_result = "/tmp/results"

    def fail_job(message: str):
        print("❌", message)
        try:
            mark_video_job_failed(token, message)
        except Exception as db_err:
            print("❌ PATCH failed error:", repr(db_err))
        return {"error": message, "token": token}

    if not image_url:
        return fail_job("image_url mancante")

    try:
        os.makedirs(tmp_result, exist_ok=True)

        subprocess.run([
            "curl",
            "-L",
            "--fail",
            "--max-time", "120",
            "-o", tmp_image,
            image_url
        ], check=True)

        if audio_url and str(audio_url).strip():
            subprocess.run([
                "curl",
                "-L",
                "--fail",
                "--max-time", "120",
                "-o", tmp_audio,
                audio_url
            ], check=True)
        else:
            if not text:
                return fail_job("Testo mancante per generazione TTS")

            subprocess.run([
    "edge-tts",
    "--text", text,
    "--voice", voice,
    "--rate", rate,
    "--pitch", pitch,
    "--write-media", tmp_audio
], check=True)

        cmd = [
            sys.executable,
            "inference.py",
            "--source_image", tmp_image,
            "--driven_audio", tmp_audio,
            "--result_dir", tmp_result,
            "--still",
            "--preprocess", "full",
            "--size", "512",
            "--expression_scale", "1.3",
            "--batch_size", "2",
            "--pose_style", "0",
        ]

        subprocess.run(cmd, check=True)

        files = glob.glob(f"{tmp_result}/**/*.mp4", recursive=True)

        if not files:
            return fail_job("Nessun video generato (.mp4 non trovato)")

        video_path = max(files, key=os.path.getctime)

        print("🎬 Video base generato:", video_path)

        final_video_path = video_path

        if plan in ["pro", "ultra"]:
            polished_path = f"/tmp/{token}_polished.mp4"

            try:
                print(f"✨ Avvio polish FFmpeg per piano: {plan}")
                polish_video_ffmpeg(video_path, polished_path)

                if not os.path.exists(polished_path):
                    return fail_job("Polish video non creato")

                polished_size = os.path.getsize(polished_path)
                print("📏 Polished video size:", polished_size)

                if polished_size < 100000:
                    return fail_job("Polish video troppo piccolo")

                final_video_path = polished_path
                print("✅ Polish FFmpeg completato:", final_video_path)

            except Exception as polish_err:
                return fail_job(f"Polish FFmpeg error: {polish_err}")

        size = os.path.getsize(final_video_path)
        print("📏 Video finale size:", size)

        if size < 100000:
            return fail_job("Video finale troppo piccolo")

        object_name = f"{token}.mp4"
        final_url = upload_to_supabase(final_video_path, token, object_name)

        if not final_url:
            return fail_job("Upload Supabase fallito")

        reel_url = None

        try:
            reel_path = f"/tmp/{token}_reel.mp4"
            create_reel_ffmpeg(final_video_path, reel_path)

            if os.path.exists(reel_path) and os.path.getsize(reel_path) > 5000:
                reel_url = upload_to_supabase(
                    reel_path,
                    token,
                    f"{token}_reel.mp4"
                )
                print("✅ Reel upload OK:", reel_url)
            else:
                print("⚠️ Reel non creato o troppo piccolo")

        except Exception as reel_err:
            print("❌ Reel creation error:", repr(reel_err))

        processing_seconds = int(time.time() - start_ts)

        try:
            db_updated = mark_video_job_done(
                token=token,
                final_url=final_url,
                reel_url=reel_url,
                processing_seconds=processing_seconds
            )
            print("✅ video_jobs aggiornato:", db_updated)
        except Exception as db_err:
            print("❌ Update DB done fallito:", repr(db_err))

        return {
            "video_url": final_url,
            "reel_url": reel_url,
            "token": token,
            "plan": plan,
            "processing_seconds": processing_seconds
        }

    except subprocess.CalledProcessError as e:
        return fail_job(f"Subprocess error: {e}")

    except Exception as e:
        return fail_job(str(e))


runpod.serverless.start({
    "handler": handler,
    "max_concurrency": 3
})
