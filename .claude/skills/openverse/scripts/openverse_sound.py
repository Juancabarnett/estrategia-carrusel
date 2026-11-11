#!/usr/bin/env python3
"""Search Openverse for open-licence sounds, download them and record credits."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/audio/"
HEADERS = {"User-Agent": "AvatarReelPack/1.0"}
SAFE_LICENSES = "cc0,pdm,by"
AUDIO_EXT = {"mp3", "wav", "ogg", "flac", "m4a", "aiff"}


def fetch(url: str, timeout: int = 30) -> bytes:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "sonido"


def probe(path: pathlib.Path) -> float | None:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            stderr=subprocess.DEVNULL,
        )
        return round(float(out.decode().strip()), 2)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def credit_line(rec: dict) -> str:
    lic = f"{rec['license']} {rec['license_version'] or ''}".strip().upper()
    return f"- {rec['title']} de {rec['creator']} ({lic}): {rec['source']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Search terms, for example whoosh or cash register.")
    parser.add_argument("--out", required=True, help="Folder for sounds and credits.")
    parser.add_argument("--limit", type=int, default=4, help="Sounds to keep.")
    parser.add_argument("--max-seconds", type=float, default=8.0, help="Longest sound to keep. Use a high value for music.")
    parser.add_argument("--min-seconds", type=float, default=0.1)
    parser.add_argument("--category", help="Optional Openverse category: sound_effect, music, podcast or audiobook.")
    parser.add_argument("--licenses", default=SAFE_LICENSES, help="Comma-separated Openverse licences.")
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    params = {"q": args.query, "license": args.licenses, "page_size": max(args.limit * 5, 20), "mature": "false"}
    if args.category:
        params["category"] = args.category
    results = json.loads(fetch(API + "?" + urllib.parse.urlencode(params))).get("results", [])

    base = slug(args.query)
    records = []
    for result in results:
        if len(records) >= args.limit:
            break
        listed = (result.get("duration") or 0) / 1000
        if listed and not (args.min_seconds <= listed <= args.max_seconds):
            continue
        ext = (result.get("filetype") or pathlib.PurePosixPath(urllib.parse.urlparse(result["url"]).path).suffix.lstrip(".")).lower()
        if ext not in AUDIO_EXT:
            continue
        name = f"{base}_{len(records) + 1}.{ext}"
        path = out / name
        try:
            path.write_bytes(fetch(result["url"]))
        except Exception:
            continue
        seconds = probe(path)
        if seconds is None or not (args.min_seconds <= seconds <= args.max_seconds):
            path.unlink(missing_ok=True)
            continue
        records.append(
            {
                "file": name,
                "query": args.query,
                "seconds": seconds,
                "title": result.get("title") or "Sin título",
                "creator": result.get("creator") or "Autor desconocido",
                "license": result.get("license"),
                "license_version": result.get("license_version"),
                "source": result.get("foreign_landing_url"),
            }
        )

    if not records:
        print(f"openverse: sin sonidos para '{args.query}'", file=sys.stderr)
        return 1

    index = out / "openverse_sound_credits.json"
    previous = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    merged = {r["file"]: r for r in previous + records}
    index.write_text(json.dumps(list(merged.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "creditos_sonido.txt").write_text(
        "Créditos de sonido:\n" + "\n".join(credit_line(r) for r in merged.values()) + "\n", encoding="utf-8"
    )
    for rec in records:
        print(f"{rec['file']} | {rec['seconds']} s | {rec['license']} {rec['license_version'] or ''} | {rec['creator']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
