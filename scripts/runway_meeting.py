#!/usr/bin/env python3
"""
Runway Characters Meeting — single CLI for all operations.

Subcommands:
  clone-yourself    Clone yourself — selfie + voice → character in one command
  create-character  Create a character step-by-step (face, voice, personality)
  clone-voice       Clone a voice from audio or generate from description
  join              Send a character to a meeting
  leave             Remove a character from a meeting
  status            Check session status
  transcript        Get post-call transcript and save to memory
  list              List your characters and presets

Usage:
  python runway_meeting.py join --meeting-url "https://meet.google.com/..." --avatar-id <id>
  python runway_meeting.py clone-yourself --name "Me" --selfie photo.jpg --voice-audio clip.m4a --personality "..."
  python runway_meeting.py leave --session-id <id>

Exit codes: 0=success, 1=error, 2=insufficient credits, 3=bad meeting URL, 4=session still active
"""

import argparse
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RUNWAY_BASE = "https://api.dev.runwayml.com"
RUNWAY_VERSION = "2024-11-06"
RAILWAY_URL = "https://runway-characters-meet-production.up.railway.app"
CONFIG_PATH = Path.home() / ".runway-characters.json"
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE = SKILL_DIR / "assets" / "monster.png"
API_KEY = os.environ.get("RUNWAYML_API_SECRET")

AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".webm": "audio/webm",
}

PRESETS = [
    {"id": "game-character", "name": "Game Character (F)", "type": "runway-preset"},
    {"id": "game-character-man", "name": "Game Character (M)", "type": "runway-preset"},
    {"id": "music-superstar", "name": "Music Superstar", "type": "runway-preset"},
    {"id": "cat-character", "name": "Cat Character", "type": "runway-preset"},
    {"id": "influencer", "name": "Influencer", "type": "runway-preset"},
    {"id": "tennis-coach", "name": "Tennis Coach", "type": "runway-preset"},
    {"id": "human-resource", "name": "Human Resource", "type": "runway-preset"},
    {"id": "fashion-designer", "name": "Fashion Designer", "type": "runway-preset"},
    {"id": "cooking-teacher", "name": "Cooking Teacher", "type": "runway-preset"},
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def require_api_key():
    if not API_KEY:
        print(
            json.dumps(
                {
                    "error": "RUNWAYML_API_SECRET is not set. Get your key at https://dev.runwayml.com"
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)


def runway(method, path, **kwargs):
    """Make an authenticated Runway API request."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "X-Runway-Version": RUNWAY_VERSION,
        "Content-Type": "application/json",
    }
    headers.update(kwargs.pop("headers", {}))
    r = requests.request(method, f"{RUNWAY_BASE}{path}", headers=headers, **kwargs)
    if r.status_code == 402:
        print(
            json.dumps(
                {
                    "error": "Insufficient Runway credits.",
                    "action": "Add credits to continue.",
                    "checkoutUrl": "https://dev.runwayml.com/billing",
                }
            ),
            file=sys.stderr,
        )
        sys.exit(2)
    if r.status_code == 204:
        return None
    data = r.json()
    if not r.ok:
        raise RuntimeError(f"Runway {method} {path} → {r.status_code}: {data}")
    return data


def upload_file(file_path: Path, content_type: str = None) -> str:
    """Upload a local file to Runway and return a runway:// URI."""
    mime = (
        content_type
        or mimetypes.guess_type(str(file_path))[0]
        or "application/octet-stream"
    )
    size_mb = file_path.stat().st_size / (1024 * 1024)

    print(f"  Uploading {file_path.name} ({size_mb:.1f}MB)...", file=sys.stderr)
    upload_meta = runway(
        "POST",
        "/v1/uploads",
        json={
            "filename": file_path.name,
            "contentType": mime,
            "type": "ephemeral",
        },
    )
    with open(file_path, "rb") as f:
        files = {k: (None, v) for k, v in upload_meta.get("fields", {}).items()}
        files["file"] = (file_path.name, f, mime)
        r = requests.post(upload_meta["uploadUrl"], files=files)
        if not r.ok:
            raise RuntimeError(f"Upload failed: {r.status_code} {r.text}")

    print("  Upload complete.", file=sys.stderr)
    return upload_meta["runwayUri"]


def poll_resource(resource_type: str, resource_id: str, timeout: int = 180) -> dict:
    """Poll a voice or avatar until READY."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(4)
        print(".", end="", flush=True, file=sys.stderr)
        r = runway("GET", f"/v1/{resource_type}/{resource_id}")
        status = r.get("status", "")
        if status == "READY":
            print(file=sys.stderr)
            return r
        if status in ("FAILED", "CANCELLED"):
            print(file=sys.stderr)
            reason = r.get("failureReason") or r.get("failure") or "unknown"
            raise RuntimeError(f"{resource_type} {resource_id} failed: {reason}")
    print(file=sys.stderr)
    raise RuntimeError(f"Timed out waiting for {resource_type} to be ready")


def poll_task(task_id: str, timeout: int = 120) -> dict:
    """Poll a generation task until SUCCEEDED."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        print(".", end="", flush=True, file=sys.stderr)
        t = runway("GET", f"/v1/tasks/{task_id}")
        if t["status"] == "SUCCEEDED":
            print(file=sys.stderr)
            return t
        if t["status"] == "FAILED":
            print(file=sys.stderr)
            raise RuntimeError(f"Generation failed: {t.get('failure', 'unknown')}")
    print(file=sys.stderr)
    raise RuntimeError("Generation timed out")


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def resolve_image(image_arg=None, description=None):
    """Resolve a face image to a Runway-compatible reference."""
    if not image_arg and not description:
        if DEFAULT_IMAGE.exists():
            return upload_file(DEFAULT_IMAGE)
        return None

    if not image_arg:
        return None  # caller will generate from description

    if image_arg.startswith("https://") or image_arg.startswith("http://"):
        return image_arg

    path = Path(image_arg)
    if not path.is_absolute():
        path = SKILL_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    return upload_file(path)


def generate_face(description: str) -> str:
    """Generate a face image from a text description."""
    print("Generating face from description...", end="", file=sys.stderr, flush=True)
    task = runway(
        "POST",
        "/v1/text_to_image",
        json={
            "model": "gemini_2.5_flash",
            "promptText": description,
            "ratio": "1248:832",
        },
    )
    result = poll_task(task["id"])
    return result["output"][0]


def resolve_voice_audio(audio_path: Path) -> str:
    """Upload an audio file and return a runway:// URI, with validation."""
    size_mb = audio_path.stat().st_size / (1024 * 1024)
    if size_mb > 10:
        raise ValueError(f"Audio file is {size_mb:.1f}MB — must be under 10MB")
    suffix = audio_path.suffix.lower()
    mime = (
        AUDIO_MIME_TYPES.get(suffix)
        or mimetypes.guess_type(str(audio_path))[0]
        or "audio/mpeg"
    )
    return upload_file(audio_path, mime)


# ---------------------------------------------------------------------------
# Subcommand: clone-yourself
# ---------------------------------------------------------------------------


def cmd_twin(args):
    """Create your digital twin in one command."""
    require_api_key()

    # --- Face ---
    reference_image = None
    if args.selfie:
        selfie_path = Path(args.selfie)
        if not selfie_path.exists():
            print(
                json.dumps({"error": f"Selfie not found: {selfie_path}"}),
                file=sys.stderr,
            )
            sys.exit(1)
        print("Uploading selfie...", end="", file=sys.stderr, flush=True)
        reference_image = upload_file(selfie_path)
        print(" done.", file=sys.stderr)
    elif args.image_url:
        reference_image = args.image_url
    elif args.face_description:
        reference_image = generate_face(args.face_description)
    else:
        if DEFAULT_IMAGE.exists():
            print(
                f"No selfie — using bundled default ({DEFAULT_IMAGE.name}).",
                file=sys.stderr,
            )
            reference_image = upload_file(DEFAULT_IMAGE)

    # --- Voice ---
    voice_config = None
    custom_voice_id = None

    if args.voice_audio:
        audio_path = Path(args.voice_audio)
        if not audio_path.exists():
            print(
                json.dumps({"error": f"Voice recording not found: {audio_path}"}),
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            f"Cloning voice from {audio_path.name}...",
            end="",
            file=sys.stderr,
            flush=True,
        )
        try:
            audio_uri = resolve_voice_audio(audio_path)
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        voice_result = runway(
            "POST",
            "/v1/voices",
            json={
                "name": f"{args.name}'s voice",
                "from": {"type": "audio", "audio": {"url": audio_uri}},
            },
        )
        custom_voice_id = voice_result["id"]
        print(" processing", end="", file=sys.stderr, flush=True)
        poll_resource("voices", custom_voice_id)
        print(f"  Voice cloned: {custom_voice_id}", file=sys.stderr)
        voice_config = {"type": "custom", "id": custom_voice_id}
    elif args.voice_id:
        custom_voice_id = args.voice_id
        voice_config = {"type": "custom", "id": args.voice_id}
    elif args.voice_description:
        if len(args.voice_description) < 20:
            print(
                json.dumps(
                    {"error": "Voice description must be at least 20 characters"}
                ),
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            "Generating voice from description...", end="", file=sys.stderr, flush=True
        )
        voice_result = runway(
            "POST",
            "/v1/voices",
            json={
                "name": f"{args.name}'s voice",
                "from": {
                    "type": "text",
                    "prompt": args.voice_description,
                    "model": "eleven_ttv_v3",
                },
            },
        )
        custom_voice_id = voice_result["id"]
        poll_resource("voices", custom_voice_id)
        print(f"  Voice generated: {custom_voice_id}", file=sys.stderr)
        voice_config = {"type": "custom", "id": custom_voice_id}
    else:
        preset = args.voice or "luna"
        print(f"Using preset voice: {preset}", file=sys.stderr)
        voice_config = {"type": "runway-live-preset", "presetId": preset}

    # --- Create character ---
    print(f'Creating character "{args.name}"...', end="", file=sys.stderr, flush=True)
    body = {
        "name": args.name,
        "personality": args.personality,
        "voice": voice_config,
        "imageProcessing": "none",
    }
    if reference_image:
        body["referenceImage"] = reference_image
    if args.start_line:
        body["startScript"] = args.start_line

    avatar = runway("POST", "/v1/avatars", json=body)
    avatar_id = avatar["id"]
    print(f" {avatar_id}", file=sys.stderr)

    if avatar["status"] != "READY":
        print("Waiting for character to be ready", end="", file=sys.stderr, flush=True)
        avatar = poll_resource("avatars", avatar_id)

    # --- Save config ---
    cfg = load_config()
    cfg["defaultCharacterId"] = avatar_id
    cfg.setdefault("characters", {})[avatar_id] = {
        "name": args.name,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "isTwin": True,
    }
    if custom_voice_id:
        cfg.setdefault("voices", {})[custom_voice_id] = {
            "name": f"{args.name}'s voice",
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "clone" if args.voice_audio else "generated",
        }
    save_config(cfg)

    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"  Your digital twin is ready!", file=sys.stderr)
    print(f"  Character: {args.name} ({avatar_id})", file=sys.stderr)
    if custom_voice_id:
        print(f"  Voice:     {custom_voice_id}", file=sys.stderr)
    print(f"  Saved to:  {CONFIG_PATH}", file=sys.stderr)
    print(f"\n  Send it to a meeting:", file=sys.stderr)
    print(
        f'    python runway_meeting.py join --meeting-url "<URL>" --avatar-id {avatar_id}',
        file=sys.stderr,
    )
    print(f"{'=' * 60}\n", file=sys.stderr)

    print(
        json.dumps(
            {
                "id": avatar_id,
                "name": args.name,
                "status": "READY",
                "voiceId": custom_voice_id,
                "type": "twin",
            },
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Subcommand: create-character
# ---------------------------------------------------------------------------


def cmd_create(args):
    """Create a character step-by-step."""
    require_api_key()

    if args.list:
        data = runway("GET", "/v1/avatars")
        avatars = data.get("data", [])
        if not avatars:
            print("No custom characters found.\n", file=sys.stderr)
            print(
                'Create one with: python runway_meeting.py create-character --name "..." --voice luna --personality "..."',
                file=sys.stderr,
            )
            print(json.dumps([]))
            sys.exit(0)
        print("\nYour Runway Characters:\n", file=sys.stderr)
        for a in avatars:
            status = "✓" if a["status"] == "READY" else f"⚠ {a['status']}"
            print(
                f"  {status}  {(a.get('name') or 'Unnamed'):<24}  id: {a['id']}",
                file=sys.stderr,
            )
        print(file=sys.stderr)
        print(
            json.dumps(
                [
                    {
                        "id": a["id"],
                        "name": a.get("name"),
                        "status": a["status"],
                        "type": "custom",
                    }
                    for a in avatars
                ],
                indent=2,
            )
        )
        sys.exit(0)

    if not args.name:
        print(json.dumps({"error": "--name is required"}), file=sys.stderr)
        sys.exit(1)
    if not args.personality:
        print(json.dumps({"error": "--personality is required"}), file=sys.stderr)
        sys.exit(1)
    if not args.voice and not args.voice_id:
        print(
            json.dumps(
                {"error": "--voice (preset) or --voice-id (custom) is required"}
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve face
    try:
        reference_image = resolve_image(args.image, args.description)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    if not reference_image and args.description:
        reference_image = generate_face(args.description)
    if not reference_image:
        print(json.dumps({"error": "Could not resolve face image"}), file=sys.stderr)
        sys.exit(1)

    # Voice config
    if args.voice_id:
        voice_config = {"type": "custom", "id": args.voice_id}
    else:
        voice_config = {"type": "runway-live-preset", "presetId": args.voice}

    # Create avatar
    print(f'Creating character "{args.name}"...', file=sys.stderr)
    body = {
        "name": args.name,
        "personality": args.personality,
        "voice": voice_config,
        "imageProcessing": "none",
    }
    if reference_image:
        body["referenceImage"] = reference_image
    if args.start_line:
        body["startScript"] = args.start_line

    avatar = runway("POST", "/v1/avatars", json=body)
    print(f"  id: {avatar['id']}", file=sys.stderr)

    if avatar["status"] != "READY":
        print("Waiting for character to be ready", end="", file=sys.stderr, flush=True)
        try:
            avatar = poll_resource("avatars", avatar["id"])
        except RuntimeError as e:
            print(json.dumps({"error": str(e), "id": avatar["id"]}), file=sys.stderr)
            sys.exit(1)

    # Save
    cfg = load_config()
    cfg["defaultCharacterId"] = avatar["id"]
    cfg.setdefault("characters", {})[avatar["id"]] = {
        "name": avatar["name"],
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save_config(cfg)

    print(f"\n✓ Character ready! Saved to {CONFIG_PATH}", file=sys.stderr)
    print(f"  Reuse this ID: --avatar-id {avatar['id']}\n", file=sys.stderr)
    print(
        json.dumps(
            {
                "id": avatar["id"],
                "name": avatar["name"],
                "status": avatar["status"],
                "type": "custom",
            },
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Subcommand: clone-voice
# ---------------------------------------------------------------------------


def cmd_clone_voice(args):
    """Clone a voice from audio or generate from description."""
    require_api_key()

    if args.list:
        data = runway("GET", "/v1/voices")
        voices = data.get("data", [])
        if not voices:
            print("No custom voices found.", file=sys.stderr)
            print(
                "Create one with: python runway_meeting.py clone-voice --name '...' --audio recording.m4a",
                file=sys.stderr,
            )
            print(json.dumps([]))
            sys.exit(0)
        print("\nYour custom voices:\n", file=sys.stderr)
        for v in voices:
            status = "✓" if v["status"] == "READY" else f"⚠ {v['status']}"
            print(
                f"  {status}  {(v.get('name') or 'Unnamed'):<28}  id: {v['id']}",
                file=sys.stderr,
            )
        print(file=sys.stderr)
        print(
            json.dumps(
                [
                    {"id": v["id"], "name": v.get("name"), "status": v["status"]}
                    for v in voices
                ],
                indent=2,
            )
        )
        sys.exit(0)

    if args.preview:
        if not args.description:
            print(
                json.dumps({"error": "--description is required for --preview"}),
                file=sys.stderr,
            )
            sys.exit(1)
        if len(args.description) < 20:
            print(
                json.dumps({"error": "Description must be at least 20 characters"}),
                file=sys.stderr,
            )
            sys.exit(1)
        print("Generating preview...", end="", file=sys.stderr, flush=True)
        result = runway(
            "POST",
            "/v1/voices/preview",
            json={"prompt": args.description, "model": "eleven_ttv_v3"},
        )
        print(file=sys.stderr)
        print(f"\n  Preview URL (24h): {result['url']}", file=sys.stderr)
        print(f"  Duration: {result['durationSecs']:.1f}s", file=sys.stderr)
        print(
            f'\n  Create it: python runway_meeting.py clone-voice --name "My Voice" --description "{args.description}"\n',
            file=sys.stderr,
        )
        print(json.dumps(result))
        sys.exit(0)

    if not args.name:
        print(json.dumps({"error": "--name is required"}), file=sys.stderr)
        sys.exit(1)
    if not args.audio and not args.description:
        print(
            json.dumps({"error": "--audio <file> or --description <text> is required"}),
            file=sys.stderr,
        )
        sys.exit(1)
    if args.audio and args.description:
        print(
            json.dumps({"error": "Provide only one of --audio or --description"}),
            file=sys.stderr,
        )
        sys.exit(1)

    if args.audio:
        audio_path = Path(args.audio)
        if not audio_path.exists():
            print(
                json.dumps({"error": f"Audio file not found: {audio_path}"}),
                file=sys.stderr,
            )
            sys.exit(1)
        print(f'Cloning voice from "{audio_path.name}"...', file=sys.stderr)
        try:
            audio_url = resolve_voice_audio(audio_path)
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        from_body = {"type": "audio", "audio": {"url": audio_url}}
    else:
        if len(args.description) < 20:
            print(
                json.dumps({"error": "Description must be at least 20 characters"}),
                file=sys.stderr,
            )
            sys.exit(1)
        print("Generating voice from description...", file=sys.stderr)
        from_body = {
            "type": "text",
            "prompt": args.description,
            "model": "eleven_ttv_v3",
        }

    try:
        result = runway(
            "POST", "/v1/voices", json={"name": args.name, "from": from_body}
        )
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    voice_id = result["id"]
    print(f"  Voice ID: {voice_id}", file=sys.stderr)

    print("Processing voice", end="", file=sys.stderr, flush=True)
    try:
        voice = poll_resource("voices", voice_id)
    except RuntimeError as e:
        print(json.dumps({"error": str(e), "id": voice_id}), file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    cfg.setdefault("voices", {})[voice_id] = {
        "name": voice.get("name", args.name),
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "clone" if args.audio else "generated",
    }
    save_config(cfg)

    preview_url = voice.get("previewUrl")
    print(f"\n✓ Voice ready! Saved to {CONFIG_PATH}", file=sys.stderr)
    print(f"  Use it: --voice-id {voice_id}", file=sys.stderr)
    if preview_url:
        print(f"  Preview: {preview_url}", file=sys.stderr)
    print(file=sys.stderr)

    print(
        json.dumps(
            {
                "id": voice_id,
                "name": voice.get("name", args.name),
                "status": "READY",
                "previewUrl": preview_url,
                "mode": "clone" if args.audio else "generated",
            },
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Subcommand: join
# ---------------------------------------------------------------------------


def cmd_join(args):
    """Send a character to a meeting."""
    require_api_key()

    if args.avatar_type == "custom" and not args.avatar_id:
        print(
            json.dumps(
                {"error": "--avatar-id is required when --avatar-type is custom"}
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    avatar_id = args.avatar_id if args.avatar_type == "custom" else args.preset_id
    avatar_type = "custom" if args.avatar_type == "custom" else "preset"

    # Resolve bot display name
    bot_name = args.bot_name
    if not bot_name:
        if avatar_type == "custom":
            try:
                avatar_info = runway("GET", f"/v1/avatars/{avatar_id}")
                bot_name = avatar_info.get("name") or "Runway Character"
            except Exception:
                bot_name = "Runway Character"
        else:
            preset_names = {p["id"]: p["name"] for p in PRESETS}
            bot_name = preset_names.get(avatar_id, "Runway Character")

    # Inject persistent memory
    personality = args.personality or ""
    if args.avatar_type == "custom" and args.avatar_id:
        memories = []
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
            memories = cfg.get("memory", {}).get(args.avatar_id, [])
        except Exception:
            pass
        if memories:
            lines = [f"- {m['date']}: {m['summary']}" for m in memories[-5:]]
            memory_ctx = (
                "Previous meeting context (use this to recall past interactions):\n"
                + "\n".join(lines)
            )
            personality = f"{memory_ctx}\n\n{personality}".strip()
            print(f"  Injecting {len(lines)} past meeting memories.", file=sys.stderr)

    # POST /api/start
    try:
        r = requests.post(
            f"{RAILWAY_URL}/api/start",
            headers={"Content-Type": "application/json", "x-runway-key": API_KEY},
            json={
                "meetingUrl": args.meeting_url,
                "avatarId": avatar_id,
                "avatarType": avatar_type,
                "botName": bot_name,
                "systemPrompt": personality,
                "meetingPassword": args.meeting_password or None,
                "maxDuration": args.max_duration,
            },
            timeout=30,
        )
    except requests.ConnectionError as e:
        print(
            json.dumps({"error": f"Could not reach Runway meeting server: {e}"}),
            file=sys.stderr,
        )
        sys.exit(1)

    if r.status_code == 402:
        print(
            json.dumps(
                {
                    "error": "Insufficient Runway credits.",
                    "action": "Add credits to continue.",
                    "checkoutUrl": "https://dev.runwayml.com/billing",
                }
            ),
            file=sys.stderr,
        )
        sys.exit(2)
    if not r.ok:
        print(
            json.dumps({"error": f"Server error {r.status_code}: {r.text}"}),
            file=sys.stderr,
        )
        sys.exit(1)

    session_id = r.json().get("sessionId")
    if not session_id:
        print(
            json.dumps({"error": "No sessionId returned from server"}), file=sys.stderr
        )
        sys.exit(1)

    # Poll until active
    print("Waiting for character to join", end="", file=sys.stderr, flush=True)
    for _ in range(90):
        time.sleep(2)
        print(".", end="", flush=True, file=sys.stderr)
        try:
            status_r = requests.get(
                f"{RAILWAY_URL}/api/sessions/{session_id}", timeout=10
            )
            session = status_r.json()
        except Exception:
            continue

        if session.get("status") == "active":
            print(file=sys.stderr)
            print(json.dumps({"sessionId": session_id, "status": "active"}))
            sys.exit(0)
        if session.get("status") == "failed":
            print(file=sys.stderr)
            err = session.get("error", "Session failed")
            code = (
                2 if "credits" in err.lower() else 3 if "meeting" in err.lower() else 1
            )
            print(json.dumps({"error": err, "sessionId": session_id}), file=sys.stderr)
            sys.exit(code)

    print(file=sys.stderr)
    print(
        json.dumps(
            {
                "error": "Timed out waiting for character to join",
                "sessionId": session_id,
            }
        ),
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommand: leave
# ---------------------------------------------------------------------------


def cmd_leave(args):
    """Remove a character from a meeting."""
    r = requests.post(
        f"{RAILWAY_URL}/api/sessions/{args.session_id}/stop",
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    data = {}
    try:
        data = r.json()
    except Exception:
        pass
    if not r.ok:
        print(
            json.dumps({"error": data.get("error", f"HTTP {r.status_code}")}),
            file=sys.stderr,
        )
        sys.exit(1)
    print(json.dumps({"ok": True}))


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------


def cmd_status(args):
    """Check session status."""
    r = requests.get(f"{RAILWAY_URL}/api/sessions/{args.session_id}", timeout=10)
    if r.status_code == 404:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)
    if not r.ok:
        print(json.dumps({"error": f"HTTP {r.status_code}"}), file=sys.stderr)
        sys.exit(1)

    session = r.json()
    duration = session.get("duration", 0)
    mins, secs = divmod(duration, 60)
    error_line = f"\n  Error: {session['error']}" if session.get("error") else ""
    print(f"\nSession: {args.session_id}", file=sys.stderr)
    print(f"  Status:   {session.get('status', 'unknown')}", file=sys.stderr)
    print(f"  Duration: {mins}m {secs}s{error_line}\n", file=sys.stderr)
    print(json.dumps(session))


# ---------------------------------------------------------------------------
# Subcommand: transcript
# ---------------------------------------------------------------------------


def cmd_transcript(args):
    """Get post-call transcript and save to memory."""
    require_api_key()

    try:
        convo = runway(
            "GET", f"/v1/avatars/{args.avatar_id}/conversations/{args.session_id}"
        )
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    status = convo.get("status")
    transcript = convo.get("transcript", [])
    recording = convo.get("recordingUrl")

    if status == "in_progress":
        print("\nConversation still in progress — call leave first.\n", file=sys.stderr)
        print(
            json.dumps({"error": "Session still active", "sessionId": args.session_id}),
            file=sys.stderr,
        )
        sys.exit(4)

    print(f"\nConversation {args.session_id}  [{status}]", file=sys.stderr)
    if convo.get("duration"):
        mins = convo["duration"] // 60
        secs = convo["duration"] % 60
        print(f"Duration: {mins}m {secs}s", file=sys.stderr)
    print(file=sys.stderr)

    if transcript:
        print("Transcript:\n", file=sys.stderr)
        for entry in transcript:
            role = entry.get("role", "?")
            content = entry.get("content", "")
            ts = entry.get("timestamp", "")
            ts_str = f" [{ts[:19].replace('T', ' ')}]" if ts else ""
            label = "Character" if role == "assistant" else "Participant"
            print(f"  {label}{ts_str}: {content}", file=sys.stderr)
        print(file=sys.stderr)
    else:
        print("  (no transcript entries)\n", file=sys.stderr)

    if recording:
        print(f"Recording: {recording}", file=sys.stderr)
        print(f"  (URL expires in 24-48 hours)\n", file=sys.stderr)

    # Save memory
    if args.save_memory:
        summary = args.summary
        if not summary and transcript:
            lines = []
            for e in transcript[:30]:
                role = "Character" if e.get("role") == "assistant" else "Participant"
                lines.append(f"{role}: {e.get('content', '')}")
            summary = " | ".join(lines)

        if summary:
            cfg = load_config()
            memory = cfg.setdefault("memory", {}).setdefault(args.avatar_id, [])
            memory.append(
                {
                    "sessionId": args.session_id,
                    "date": time.strftime("%Y-%m-%d"),
                    "summary": summary[:500],
                }
            )
            cfg["memory"][args.avatar_id] = memory[-10:]
            save_config(cfg)
            print(f"✓ Memory saved to {CONFIG_PATH}", file=sys.stderr)
            print("  Context will be injected on the next join.\n", file=sys.stderr)
        else:
            print(
                "  Nothing to save (no transcript and no --summary provided)\n",
                file=sys.stderr,
            )

    print(
        json.dumps(
            {
                "sessionId": args.session_id,
                "avatarId": args.avatar_id,
                "status": status,
                "duration": convo.get("duration"),
                "transcript": transcript,
                "recordingUrl": recording,
            },
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Subcommand: list
# ---------------------------------------------------------------------------


def cmd_list(args):
    """List characters and presets."""
    require_api_key()

    custom_avatars = []
    try:
        r = requests.get(
            f"{RAILWAY_URL}/api/avatars",
            headers={"x-runway-key": API_KEY},
            timeout=10,
        )
        if r.ok:
            custom_avatars = r.json()
    except Exception:
        pass

    print("\nAvailable Characters:\n", file=sys.stderr)
    print("  Preset avatars (no setup required):", file=sys.stderr)
    for p in PRESETS:
        print(
            f"    --avatar-type runway-preset --preset-id {p['id']:<22} → {p['name']}",
            file=sys.stderr,
        )

    if custom_avatars:
        print("\n  Your custom characters:", file=sys.stderr)
        for a in custom_avatars:
            name = a.get("name") or "Unnamed"
            print(
                f"    --avatar-type custom --avatar-id {a['id']}  → {name}",
                file=sys.stderr,
            )
    print(file=sys.stderr)

    all_avatars = PRESETS + [
        {"id": a["id"], "name": a.get("name", "Unnamed"), "type": "custom"}
        for a in custom_avatars
    ]
    print(json.dumps(all_avatars, indent=2))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        prog="runway_meeting",
        description="Runway Characters Meeting — send AI characters to video calls",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- clone-yourself ---
    p = sub.add_parser(
        "clone-yourself",
        help="Clone yourself — selfie + voice → character in one command",
    )
    p.add_argument("--name", required=True, help="Character name")
    p.add_argument("--personality", required=True, help="System prompt / personality")
    face = p.add_mutually_exclusive_group()
    face.add_argument("--selfie", help="Path to selfie image")
    face.add_argument("--image-url", help="HTTPS URL to face image")
    face.add_argument("--face-description", help="Generate face from text")
    voice = p.add_mutually_exclusive_group()
    voice.add_argument("--voice-audio", help="Audio file for voice cloning (10s-5min)")
    voice.add_argument("--voice", help="Preset voice ID (e.g. luna, maya)")
    voice.add_argument("--voice-description", help="Generate voice from text")
    voice.add_argument("--voice-id", help="Existing custom voice ID")
    p.add_argument("--start-line", help="Opening line when joining")
    p.set_defaults(func=cmd_twin)

    # --- create-character ---
    p = sub.add_parser("create-character", help="Create a character step-by-step")
    p.add_argument("--name", help="Character name")
    p.add_argument("--personality", help="System prompt / personality")
    p.add_argument("--voice", help="Preset voice ID")
    p.add_argument("--voice-id", dest="voice_id", help="Custom voice ID")
    p.add_argument("--image", help="Face image: local file or HTTPS URL")
    p.add_argument("--description", help="Generate face from text")
    p.add_argument("--start-line", help="Opening line when joining")
    p.add_argument("--list", action="store_true", help="List existing characters")
    p.set_defaults(func=cmd_create)

    # --- clone-voice ---
    p = sub.add_parser(
        "clone-voice", help="Clone voice from audio or generate from description"
    )
    p.add_argument("--name", help="Voice name")
    p.add_argument("--audio", help="Audio file for cloning (10s-5min, <10MB)")
    p.add_argument("--description", help="Text description (min 20 chars)")
    p.add_argument("--preview", action="store_true", help="Preview before creating")
    p.add_argument("--list", action="store_true", help="List existing voices")
    p.set_defaults(func=cmd_clone_voice)

    # --- join ---
    p = sub.add_parser("join", help="Send character to a meeting")
    p.add_argument("--meeting-url", required=True, help="Zoom, Meet, or Teams URL")
    p.add_argument(
        "--avatar-type", default="custom", choices=["custom", "runway-preset"]
    )
    p.add_argument("--avatar-id", help="Character UUID")
    p.add_argument("--preset-id", default="game-character", help="Preset ID")
    p.add_argument(
        "--personality", default="", help="Override personality for this meeting"
    )
    p.add_argument("--meeting-password", default="", help="Meeting password (Zoom)")
    p.add_argument("--bot-name", default="", help="Display name in meeting (defaults to character name)")
    p.add_argument(
        "--max-duration",
        type=int,
        default=300,
        help="Max session seconds (max 300 seconds)",
    )
    p.set_defaults(func=cmd_join)

    # --- leave ---
    p = sub.add_parser("leave", help="Remove character from meeting")
    p.add_argument("--session-id", required=True, help="Session ID from join")
    p.set_defaults(func=cmd_leave)

    # --- status ---
    p = sub.add_parser("status", help="Check session status")
    p.add_argument("--session-id", required=True, help="Session ID from join")
    p.set_defaults(func=cmd_status)

    # --- transcript ---
    p = sub.add_parser("transcript", help="Get transcript and save to memory")
    p.add_argument("--avatar-id", required=True, help="Character UUID")
    p.add_argument("--session-id", required=True, help="Session/conversation ID")
    p.add_argument(
        "--save-memory", action="store_true", help="Save to character memory"
    )
    p.add_argument("--summary", help="Custom summary text")
    p.set_defaults(func=cmd_transcript)

    # --- list ---
    p = sub.add_parser("list", help="List characters and presets")
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
