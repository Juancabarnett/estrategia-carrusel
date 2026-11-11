#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CANON = SKILL_DIR / "references" / "avatar_reel_post_canon.json"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ffprobe(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)


def add(checks: list[dict[str, Any]], name: str, passed: bool, evidence: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "evidence": evidence})


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate canonical Avatar Reel post-production sidecars.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--final", required=True)
    parser.add_argument("--canon", default=str(DEFAULT_CANON))
    parser.add_argument("--out")
    parser.add_argument("--require-title", action="store_true")
    parser.add_argument("--require-music", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    final = Path(args.final)
    canon = load_json(Path(args.canon))
    if canon is None:
        raise SystemExit(f"Missing canon file: {args.canon}")

    checks: list[dict[str, Any]] = []

    probe = ffprobe(final)
    add(checks, "final_exists", final.exists(), str(final))
    if probe:
        video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
        audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
        v0 = video_streams[0] if video_streams else {}
        add(checks, "final_has_video", bool(video_streams), json.dumps(v0))
        add(checks, "final_has_audio", bool(audio_streams), f"{len(audio_streams)} audio stream(s)")
        add(
            checks,
            "final_is_1080x1920",
            int(v0.get("width", 0)) == canon["layout"]["width"] and int(v0.get("height", 0)) == canon["layout"]["height"],
            f"{v0.get('width')}x{v0.get('height')}",
        )
    else:
        add(checks, "ffprobe_final", False, "ffprobe failed or final missing")

    title_manifest = load_json(run_dir / canon["title"]["manifest"])
    if args.require_title:
        add(checks, "title_manifest_exists", title_manifest is not None, canon["title"]["manifest"])
    if title_manifest:
        card = title_manifest.get("card", {})
        layout = title_manifest.get("layout", {})
        colors = title_manifest.get("colors", {})
        add(checks, "title_radius_24", card.get("radius") == canon["title"]["card"]["radius"], str(card.get("radius")))
        add(checks, "title_background", card.get("background") == canon["title"]["card"]["background"], str(card.get("background")))
        add(checks, "title_line_2_color", colors.get("line_2") == canon["title"]["colors"]["line_2"], str(colors.get("line_2")))
        add(checks, "title_centered_on_split", layout.get("center_y") == canon["layout"]["split_line_y"], str(layout.get("center_y")))

    captions_style = load_json(run_dir / "captions_style.json")
    add(checks, "captions_style_exists", captions_style is not None, "captions_style.json")
    if captions_style:
        add(checks, "captions_split_line", captions_style.get("split_line_y") == canon["layout"]["split_line_y"], str(captions_style.get("split_line_y")))
        add(checks, "captions_title_active_y", captions_style.get("title_active_y") == canon["captions"]["title_active_y"], str(captions_style.get("title_active_y")))
        add(checks, "captions_default_y", captions_style.get("default_y") == canon["captions"]["default_y"], str(captions_style.get("default_y")))
        add(checks, "captions_max_3_words", captions_style.get("max_words_per_caption") == canon["captions"]["max_words_per_caption"], str(captions_style.get("max_words_per_caption")))

    mix_manifest = load_json(run_dir / "final_mix_manifest.json")
    add(checks, "final_mix_manifest_exists", mix_manifest is not None, "final_mix_manifest.json")
    if mix_manifest:
        music = mix_manifest.get("music")
        add(checks, "music_present_or_explicitly_skipped", bool(music) or bool(mix_manifest.get("music_skipped")), str(music or mix_manifest.get("music_skip_reason")))
        if args.require_music:
            add(checks, "music_required_and_present", bool(music), str(music))
        if music:
            user_feedback_override = bool(mix_manifest.get("user_feedback_override"))
            vol = float(mix_manifest.get("music_volume", 0))
            expected = canon["audio"]["music_volume_range"]
            volume_ok = expected[0] <= vol <= expected[1] or user_feedback_override
            add(checks, "music_volume_in_canon_range_or_user_override", volume_ok, f"{vol} override={user_feedback_override}")
            duck = mix_manifest.get("ducking", {}) or mix_manifest.get("filters", {}).get("ducking", {})
            if not isinstance(duck, dict):
                duck = {"mode": str(duck)}
            threshold = duck.get("threshold")
            threshold_range = canon["audio"]["ducking"].get("threshold_range")
            if threshold_range and threshold is not None:
                threshold_ok = threshold_range[0] <= float(threshold) <= threshold_range[1] or user_feedback_override
            else:
                threshold_ok = threshold == canon["audio"]["ducking"]["threshold"] or user_feedback_override
            ratio = duck.get("ratio")
            ratio_range = canon["audio"]["ducking"].get("ratio_range")
            if ratio_range and ratio is not None:
                ratio_ok = ratio_range[0] <= float(ratio) <= ratio_range[1] or user_feedback_override
            else:
                ratio_ok = ratio == canon["audio"]["ducking"]["ratio"] or user_feedback_override
            add(checks, "ducking_threshold_in_canon_range_or_user_override", threshold_ok, f"{threshold} override={user_feedback_override}")
            add(checks, "ducking_ratio_in_canon_range_or_user_override", ratio_ok, f"{ratio} override={user_feedback_override}")

    passed = all(check["passed"] for check in checks)
    report = {
        "passed": passed,
        "checks": checks,
        "canon": {"file": str(Path(args.canon).resolve()), "version": canon["version"]},
    }
    out = Path(args.out) if args.out else run_dir / "post_render_qa_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
