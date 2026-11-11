#!/usr/bin/env python3
"""Data Nube API tool: voice, avatar render, music and balances.

Works in two places:
- On the local PC it reads keys from .env.
- In Claude Code cloud sessions there is no .env. The keys live in the
  environment's network secrets and the proxy adds them, so requests go out
  without a key header.

Usage:
  python3 scripts/dn.py balances
  python3 scripts/dn.py tts RUN_DIR SCRIPT_FILE [--out audio_final.mp3]
  python3 scripts/dn.py heygen-render RUN_DIR [--audio audio_final.mp3] [--title TITLE]
  python3 scripts/dn.py music RUN_DIR PROMPT_JSON
"""
import argparse, json, os, pathlib, sys, time, urllib.error, urllib.request, uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDENTITY = ROOT / ".claude" / "skills" / "avatar-reel" / "identity.json"
UA = "DataNubeReel/1.0"


def load_env():
    """Read .env into os.environ without overriding values already set."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def key_headers(service):
    """Auth header for a service, or none when the cloud proxy injects it."""
    names = {"heygen": ("HEYGEN_API_KEY", "x-api-key", ""),
             "elevenlabs": ("ELEVENLABS_API_KEY", "xi-api-key", ""),
             "kie": ("KIE_API_KEY", "Authorization", "Bearer ")}
    env, header, prefix = names[service]
    value = os.environ.get(env, "").strip()
    return {header: prefix + value} if value else {}


def call(url, service, body=None, headers=None, timeout=120, raw=False):
    h = {"User-Agent": UA, **key_headers(service), **(headers or {})}
    data = None
    if body is not None and not isinstance(body, (bytes, bytearray)):
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    elif body is not None:
        data = body
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            return (payload, r.headers) if raw else json.loads(payload or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace")
        sys.exit(f"{service} HTTP {e.code}: {detail}")


def identity():
    return json.loads(IDENTITY.read_text(encoding="utf-8"))["identities"]["me"]


def cmd_balances(_):
    heygen = call("https://api.heygen.com/v3/users/me", "heygen")
    eleven = call("https://api.elevenlabs.io/v1/user/subscription", "elevenlabs")
    kie = call("https://api.kie.ai/api/v1/chat/credit", "kie")
    print(json.dumps({
        "heygen_usd": (heygen.get("data") or {}).get("wallet", {}).get("remaining_balance"),
        "elevenlabs_chars_left": (eleven.get("character_limit") or 0) - (eleven.get("character_count") or 0),
        "kie_credits": kie.get("data"),
    }, ensure_ascii=False))


def cmd_tts(a):
    run = pathlib.Path(a.run_dir); run.mkdir(parents=True, exist_ok=True)
    tts = identity()["voice_generation_canon"]["elevenlabs_tts"]
    text = pathlib.Path(a.script_file).read_text(encoding="utf-8").strip()
    settings = {"stability": a.stability, "similarity_boost": a.similarity}
    body = {"text": text, "model_id": tts["model_id"], "language_code": tts["language_code"], "voice_settings": settings}
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{tts['voice_id']}?output_format={tts['output_format']}"
    audio, headers = call(url, "elevenlabs", body=body, timeout=240, raw=True)
    out = run / a.out
    out.write_bytes(audio)
    (run / "voice_generation.json").write_text(json.dumps({
        "provider": "elevenlabs", "voice_id": tts["voice_id"], "model_id": tts["model_id"], "settings": settings,
        "script_file": str(a.script_file), "character_cost": headers.get("character-cost")}, indent=2) + "\n", encoding="utf-8")
    print(f"ok {out} ({len(audio)} bytes, cost {headers.get('character-cost')} chars)")


def upload_audio(run, audio):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{audio.name}\"\r\n"
            "Content-Type: audio/mpeg\r\n\r\n").encode() + audio.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    res = call("https://api.heygen.com/v3/assets", "heygen", body=body,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=240)
    (run / "asset_upload.raw.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    return res["data"]["asset_id"]


def cmd_heygen_render(a):
    """Creates the render once. Rerunning resumes the saved video_id instead of paying again."""
    run = pathlib.Path(a.run_dir)
    created = run / "video_create.raw.json"
    video_id = None
    if created.exists():
        video_id = (json.loads(created.read_text(encoding="utf-8")).get("data") or {}).get("video_id")
    if not video_id:
        avatar = identity()["heygen_avatar_id"]
        look = call(f"https://api.heygen.com/v3/avatars/looks/{avatar}", "heygen").get("data") or {}
        if "avatar_v" not in (look.get("supported_api_engines") or []):
            sys.exit("avatar_v_unavailable: the look does not support Avatar V")
        asset = upload_audio(run, run / a.audio)
        body = {"type": "avatar", "avatar_id": avatar, "audio_asset_id": asset, "engine": {"type": "avatar_v"},
                "aspect_ratio": "16:9", "resolution": "720p", "output_format": "mp4", "title": a.title}
        (run / "video_request.body.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        res = call("https://api.heygen.com/v3/videos", "heygen", body=body)
        created.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        video_id = res["data"]["video_id"]
    print("video_id", video_id, flush=True)
    for _ in range(90):
        status = call(f"https://api.heygen.com/v3/videos/{video_id}", "heygen").get("data") or {}
        state = status.get("status")
        if state == "completed":
            video, _ = call(status["video_url"], "heygen", raw=True, timeout=300)
            (run / "video_avatar.mp4").write_bytes(video)
            (run / "video_result.json").write_text(json.dumps({
                "provider": "heygen", "api_path": "/v3/videos", "engine": {"type": "avatar_v"},
                "video_id": video_id, "status": "completed", "duration": status.get("duration")}, indent=2) + "\n", encoding="utf-8")
            print("completed", run / "video_avatar.mp4")
            return
        if state in ("failed", "error"):
            sys.exit(f"render failed: {status.get('failure_message') or status}")
        time.sleep(20)
    sys.exit("still rendering: rerun the same command to keep waiting (no new charge)")


def cmd_music(a):
    """Creates one Suno task (or resumes it) and downloads both variants."""
    run = pathlib.Path(a.run_dir)
    task_file = run / "music_task.json"
    if task_file.exists():
        task = json.loads(task_file.read_text(encoding="utf-8"))["taskId"]
    else:
        prompt = json.loads(pathlib.Path(a.prompt_json).read_text(encoding="utf-8"))
        prompt.setdefault("callBackUrl", "https://example.com/no-callback")
        prompt["instrumental"] = True
        (run / "music_prompt.json").write_text(json.dumps(prompt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        res = call("https://api.kie.ai/api/v1/generate", "kie", body=prompt)
        task = (res.get("data") or {}).get("taskId")
        if not task:
            sys.exit(f"kie create failed: {res}")
        task_file.write_text(json.dumps({"taskId": task, "provider": "suno_via_kie"}, indent=2) + "\n", encoding="utf-8")
    print("taskId", task, flush=True)
    for _ in range(40):
        data = call(f"https://api.kie.ai/api/v1/generate/record-info?taskId={task}", "kie").get("data") or {}
        state = data.get("status") or ""
        tracks = (data.get("response") or {}).get("sunoData") or []
        if state == "SUCCESS" and tracks:
            for n, t in enumerate(tracks, 1):
                req = urllib.request.Request(t.get("audioUrl") or t.get("sourceAudioUrl"), headers={"User-Agent": "Mozilla/5.0"})
                (run / f"music_v{n}.mp3").write_bytes(urllib.request.urlopen(req, timeout=180).read())
                print("variant", n, "duration", t.get("duration"))
            return
        if any(s in state for s in ("FAILED", "ERROR", "SENSITIVE")):
            sys.exit(f"music failed: {state}")
        time.sleep(15)
    sys.exit("still generating: rerun the same command to keep waiting (no new charge)")


def main():
    load_env()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("balances").set_defaults(fn=cmd_balances)
    t = sub.add_parser("tts"); t.add_argument("run_dir"); t.add_argument("script_file")
    t.add_argument("--out", default="audio_final.mp3"); t.add_argument("--stability", type=float, default=0.2)
    t.add_argument("--similarity", type=float, default=0.75); t.set_defaults(fn=cmd_tts)
    h = sub.add_parser("heygen-render"); h.add_argument("run_dir"); h.add_argument("--audio", default="audio_final.mp3")
    h.add_argument("--title", default="Data Nube reel"); h.set_defaults(fn=cmd_heygen_render)
    m = sub.add_parser("music"); m.add_argument("run_dir"); m.add_argument("prompt_json"); m.set_defaults(fn=cmd_music)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
