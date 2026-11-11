#!/usr/bin/env python3
"""Resolve and validate avatar-reel speaker identity before voice/avatar render."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "identity.json"


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, help="Avatar reel run folder.")
    parser.add_argument("--owner", help="Intended speaker owner key in identity.json, e.g. me.")
    parser.add_argument("--avatar-id", help="Explicit HeyGen avatar_id.")
    parser.add_argument("--voice-id", help="Explicit ElevenLabs voice_id.")
    args = parser.parse_args()

    run_dir = pathlib.Path(args.run_dir)
    run_json = run_dir / "run.json"
    run = load_json(run_json) if run_json.exists() else {}
    params = run.get("params") or {}
    concept = run.get("concept") or {}
    cfg = load_json(CONFIG)

    owner = first_text(args.owner, params.get("avatar_owner"), run.get("avatar_owner"), concept.get("avatar_owner"))
    owner = owner or cfg["default_owner"]
    identities = cfg.get("identities") or {}
    if owner not in identities:
        raise SystemExit(f"identity_guard: unknown avatar owner '{owner}'. Add it to {CONFIG}.")

    identity = identities[owner]
    avatar_id = first_text(args.avatar_id, params.get("avatar_id"), run.get("avatar_id"), identity.get("heygen_avatar_id"))
    voice_id = first_text(args.voice_id, params.get("elevenlabs_voice_id"), params.get("voice_id"), run.get("elevenlabs_voice_id"), identity.get("elevenlabs_voice_id"))

    if not avatar_id:
        raise SystemExit("identity_guard: missing heygen avatar_id after identity resolution.")
    if not voice_id:
        raise SystemExit("identity_guard: missing elevenlabs voice_id after identity resolution.")

    blocked = cfg.get("blocked_unless_explicit_owner") or {}
    for blocked_owner, spec in blocked.items():
        blocked_avatar = spec.get("heygen_avatar_id")
        blocked_voice = spec.get("elevenlabs_voice_id")
        if owner != blocked_owner and blocked_avatar and avatar_id == blocked_avatar:
            raise SystemExit(
                f"identity_guard: blocked avatar_id {avatar_id} belongs to '{blocked_owner}', "
                f"not '{owner}'. {spec.get('reason', '')}".strip()
            )
        if owner != blocked_owner and blocked_voice and voice_id == blocked_voice:
            raise SystemExit(
                f"identity_guard: blocked voice_id {voice_id} belongs to '{blocked_owner}', "
                f"not '{owner}'. {spec.get('reason', '')}".strip()
            )

    sidecar = {
        "status": "pass",
        "owner": owner,
        "display_name": identity.get("display_name", owner),
        "heygen_avatar_id": avatar_id,
        "elevenlabs_voice_id": voice_id,
        "elevenlabs_voice_name": identity.get("elevenlabs_voice_name"),
        "voice_generation_canon": identity.get("voice_generation_canon"),
        "visual_spec": identity.get("visual_spec"),
        "visual_reference_dir": identity.get("visual_reference_dir"),
        "source": {
            "owner": "explicit_or_default_identity",
            "avatar_id": "explicit_or_identity_json",
            "voice_id": "explicit_or_identity_json"
        },
        "blocked_identities_enforced": list(blocked.keys())
    }
    (run_dir / cfg.get("required_sidecar", "identity_guard.json")).write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    sys.stdout.write(json.dumps(sidecar, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
