#!/usr/bin/env python3
"""Search Openverse for open-licence images, download them and record credits."""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

API = "https://api.openverse.org/v1/images/"
HEADERS = {"User-Agent": "AvatarReelPack/1.0"}
SAFE_LICENSES = "cc0,pdm,by"


def fetch(url: str, timeout: int = 20) -> bytes:
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
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "imagen"


def credit_line(rec: dict) -> str:
    lic = f"{rec['license']} {rec['license_version'] or ''}".strip().upper()
    return f"- {rec['title']} de {rec['creator']} ({lic}): {rec['source']}"


def contact_sheet(items: list[tuple[str, Image.Image]], path: pathlib.Path) -> None:
    cell, label, cols = 300, 30, 4
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label)), (250, 247, 242))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    for i, (name, img) in enumerate(items):
        thumb = img.copy()
        thumb.thumbnail((cell - 8, cell - 8))
        x, y = (i % cols) * cell, (i // cols) * (cell + label)
        sheet.paste(thumb, (x + 4, y + label))
        draw.text((x + 6, y + 5), name[:30], fill=(20, 20, 20), font=font)
    sheet.save(path, quality=88)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Search terms. English usually returns more results.")
    parser.add_argument("--out", required=True, help="Folder for images, credits and the contact sheet.")
    parser.add_argument("--limit", type=int, default=4, help="Images to keep.")
    parser.add_argument("--min-width", type=int, default=900)
    parser.add_argument("--min-height", type=int, default=0, help="Checked on the downloaded file. Use about 1200 for full-screen vertical use.")
    parser.add_argument("--aspect", choices=["tall", "wide", "square"], help="Use tall for full-screen vertical video.")
    parser.add_argument("--size", choices=["small", "medium", "large"], help="Openverse size filter.")
    parser.add_argument("--source", help="Openverse sources, for example stocksnap or wikimedia. These two have high-resolution files.")
    parser.add_argument("--licenses", default=SAFE_LICENSES, help="Comma-separated Openverse licences.")
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    params = {"q": args.query, "license": args.licenses, "page_size": max(args.limit * 6, 20), "mature": "false"}
    if args.aspect:
        params["aspect_ratio"] = args.aspect
    if args.size:
        params["size"] = args.size
    if args.source:
        params["source"] = args.source
    results = json.loads(fetch(API + "?" + urllib.parse.urlencode(params))).get("results", [])

    base = slug(args.query)
    records, items = [], []
    for result in results:
        if len(records) >= args.limit:
            break
        if (result.get("width") or 0) < args.min_width:
            continue
        try:
            img = Image.open(io.BytesIO(fetch(result["url"], 15))).convert("RGB")
        except Exception:
            continue
        if img.height < args.min_height:
            continue
        name = f"{base}_{len(records) + 1}.jpg"
        img.thumbnail((2400, 2400))
        img.save(out / name, quality=90)
        records.append(
            {
                "file": name,
                "query": args.query,
                "title": result.get("title") or "Sin título",
                "creator": result.get("creator") or "Autor desconocido",
                "license": result.get("license"),
                "license_version": result.get("license_version"),
                "source": result.get("foreign_landing_url"),
            }
        )
        items.append((name, img))

    if not records:
        print(f"openverse: sin resultados para '{args.query}'", file=sys.stderr)
        return 1

    index = out / "openverse_credits.json"
    previous = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    merged = {r["file"]: r for r in previous + records}
    index.write_text(json.dumps(list(merged.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "creditos_openverse.txt").write_text(
        "Créditos de imágenes:\n" + "\n".join(credit_line(r) for r in merged.values()) + "\n", encoding="utf-8"
    )
    contact_sheet(items, out / f"_hoja_{base}.jpg")
    for rec in records:
        print(f"{rec['file']} | {rec['license']} {rec['license_version'] or ''} | {rec['creator']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
