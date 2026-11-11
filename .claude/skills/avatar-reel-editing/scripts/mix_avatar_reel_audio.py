#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CANON = SKILL_DIR / "references" / "avatar_reel_post_canon.json"

# Integrated-loudness gate for voice premaster and final master (target I=-16).
LUFS_MIN = -17.0
LUFS_MAX = -13.0


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed: "
            + " ".join(cmd)
            + "\nSTDOUT:\n"
            + proc.stdout[-3000:]
            + "\nSTDERR:\n"
            + proc.stderr[-3000:]
        )
    return proc


def load_canon(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def probe_duration(path: Path) -> float | None:
    try:
        proc = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]
        )
        return float(proc.stdout.strip())
    except Exception:
        return None


def measure_lufs(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "loudnorm=print_format=json",
            "-f",
            "null",
            "-",
        ],
        text=True,
        capture_output=True,
    )
    tail = proc.stderr[proc.stderr.rfind("{"):]
    tail = tail[: tail.rfind("}") + 1]
    return float(json.loads(tail)["input_i"])


def premaster_voice(input_video: Path, out: Path, canon: dict[str, Any]) -> tuple[Path, float]:
    """Normalize the voice track to a wav before mixing.

    Single-pass dynamic loudnorm only: TTS masters can sit ~19 dB low, and a
    measured_*/linear=true second pass gets blocked by the TP constraint there,
    leaving the output unnormalized. The staged wav makes the result verifiable.
    """
    voice_wav = out.parent / f"{out.stem}_voice_premaster.wav"
    # loudnorm must be the last gain stage: a compressor after it pulls the
    # normalized voice several dB back under target.
    voice_filter = (
        "acompressor=threshold=-18dB:ratio=2:attack=10:release=120,"
        f"loudnorm={canon['audio']['voice_processing']['loudnorm']},"
        "alimiter=limit=0.95"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            str(input_video),
            "-vn",
            "-af",
            voice_filter,
            "-ar",
            "48000",
            str(voice_wav),
        ]
    )
    voice_lufs = measure_lufs(voice_wav)
    if not (LUFS_MIN <= voice_lufs <= LUFS_MAX):
        raise RuntimeError(
            f"voice premaster off target: {voice_lufs} LUFS (expected {LUFS_MIN}..{LUFS_MAX})"
        )
    return voice_wav, voice_lufs


def check_final_lufs(out: Path) -> float:
    final_lufs = measure_lufs(out)
    if not (LUFS_MIN <= final_lufs <= LUFS_MAX):
        raise RuntimeError(
            f"final mix off target: {final_lufs} LUFS (expected {LUFS_MIN}..{LUFS_MAX})"
        )
    return final_lufs


def build_mix_filter(canon: dict[str, Any], music_volume: float) -> str:
    duck = canon["audio"]["ducking"]
    return (
        f"[1:a]volume={music_volume:.4f}[music_base];"
        f"[music_base][0:a]sidechaincompress="
        f"threshold={duck['threshold']}:ratio={duck['ratio']}:"
        f"attack={duck['attack']}:release={duck['release']}[music_ducked];"
        "[0:a][music_ducked]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95[outa]"
    )


def render_with_music(args: argparse.Namespace, canon: dict[str, Any]) -> dict[str, Any]:
    input_video = Path(args.input)
    music = Path(args.music)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    music_volume = args.music_volume if args.music_volume is not None else float(canon["audio"]["music_volume_default"])

    voice_wav, voice_lufs = premaster_voice(input_video, out, canon)

    filter_complex = build_mix_filter(canon, music_volume)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        str(voice_wav),
        "-stream_loop",
        "-1",
        "-i",
        str(music),
        "-i",
        str(input_video),
        "-filter_complex",
        filter_complex,
        "-map",
        "2:v:0",
        "-map",
        "[outa]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out),
    ]
    run(cmd)
    final_lufs = check_final_lufs(out)
    return {
        "input": str(input_video),
        "music": str(music),
        "output": str(out),
        "music_volume": music_volume,
        "ducking": canon["audio"]["ducking"],
        "mixing": canon["audio"]["mixing"],
        "voice_processing": {
            **canon["audio"]["voice_processing"],
            "staged_premaster": str(voice_wav),
            "loudnorm_mode": "dynamic_single_pass",
        },
        "measured": {
            "voice_premaster_lufs": voice_lufs,
            "final_lufs": final_lufs,
            "lufs_gate": [LUFS_MIN, LUFS_MAX],
        },
        "filter_complex": filter_complex,
        "duration_s": probe_duration(out),
        "canon_version": canon["version"],
    }


def render_without_music(args: argparse.Namespace, canon: dict[str, Any]) -> dict[str, Any]:
    input_video = Path(args.input)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    voice_wav, voice_lufs = premaster_voice(input_video, out, canon)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        str(input_video),
        "-i",
        str(voice_wav),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out),
    ]
    run(cmd)
    final_lufs = check_final_lufs(out)
    return {
        "input": str(input_video),
        "music": None,
        "music_skipped": True,
        "music_skip_reason": args.music_skip_reason,
        "output": str(out),
        "voice_processing": {
            **canon["audio"]["voice_processing"],
            "staged_premaster": str(voice_wav),
            "loudnorm_mode": "dynamic_single_pass",
        },
        "measured": {
            "voice_premaster_lufs": voice_lufs,
            "final_lufs": final_lufs,
            "lufs_gate": [LUFS_MIN, LUFS_MAX],
        },
        "duration_s": probe_duration(out),
        "canon_version": canon["version"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Mix Avatar Reel voice and music with canonical ducking.")
    parser.add_argument("--input", required=True, help="Captioned/composite video with voice audio.")
    parser.add_argument("--music", help="music.mp3. Required unless --allow-no-music is set.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--canon", default=str(DEFAULT_CANON))
    parser.add_argument("--music-volume", type=float)
    parser.add_argument("--allow-no-music", action="store_true")
    parser.add_argument("--music-skip-reason", default="explicit_no_music")
    args = parser.parse_args()

    canon = load_canon(Path(args.canon))
    if args.music:
        manifest = render_with_music(args, canon)
    elif args.allow_no_music:
        manifest = render_without_music(args, canon)
    else:
        raise SystemExit("--music is required unless --allow-no-music is set")

    manifest["canon"] = {"file": str(Path(args.canon).resolve()), "version": canon["version"]}
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
