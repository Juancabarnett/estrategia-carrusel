#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CANON = SKILL_DIR / "references" / "avatar_reel_post_canon.json"


def load_canon(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hex_to_rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {value!r}")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def resolve_font(canon: dict[str, Any], explicit: str | None) -> Path | None:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    candidates.extend(canon["title"]["font"].get("paths", []))
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.exists():
            return path
    return None


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=font)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int]:
    bbox = text_bbox(draw, text, font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def load_font(path: Path | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path is None:
        return ImageFont.load_default(size=size)
    return ImageFont.truetype(str(path), size=size)


def fit_font(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font_path: Path | None,
    card_width: int,
    card_height: int,
    padding_x: int,
    padding_y: int,
    line_gap: int,
    size_min: int,
    size_max: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    available_w = card_width - padding_x * 2
    available_h = card_height - padding_y * 2
    # keep searching below size_min rather than silently overflowing the card
    hard_floor = 16
    for size in range(size_max, hard_floor - 1, -1):
        font = load_font(font_path, size)
        widths = [text_size(draw, line, font)[0] for line in lines]
        heights = [text_size(draw, line, font)[1] for line in lines]
        total_h = sum(heights) + line_gap * (len(lines) - 1)
        if max(widths, default=0) <= available_w and total_h <= available_h:
            return font
    return load_font(font_path, hard_floor)


def normalize_lines(line1: str, line2: str | None) -> list[str]:
    lines = [line1.strip().upper()]
    if line2 and line2.strip():
        lines.append(line2.strip().upper())
    words = " ".join(lines).split()
    if len(lines) > 2:
        raise ValueError("Title supports at most 2 lines")
    if len(words) > 6:
        raise ValueError("Title supports at most 6 words")
    if not lines[0]:
        raise ValueError("line1 is required")
    return lines


def render(args: argparse.Namespace) -> None:
    canon = load_canon(Path(args.canon))
    title = canon["title"]
    card = title["card"]
    font_cfg = title["font"]
    colors = title["colors"]
    lines = normalize_lines(args.line1, args.line2)

    width = int(args.width or card["width"])
    height = int(args.height or card["height"])
    radius = int(args.radius or card["radius"])
    padding_x = int(card["padding_x"])
    padding_y = int(card["padding_y"])
    line_gap = int(font_cfg["line_gap"])

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (0, 0, width, height),
        radius=radius,
        fill=hex_to_rgba(card["background"]),
    )

    font_path = resolve_font(canon, args.font_path)
    font = fit_font(
        draw,
        lines,
        font_path,
        width,
        height,
        padding_x,
        padding_y,
        line_gap,
        int(font_cfg["size_min"]),
        int(font_cfg["size_max"]),
    )

    # center the actual ink box: PIL draws relative to the glyph origin, so the
    # rendered ink lands bbox[0]/bbox[1] pixels right/below the draw position.
    # Subtract those offsets or the text sits visibly low (and off-center).
    bboxes = [text_bbox(draw, line, font) for line in lines]
    heights = [b[3] - b[1] for b in bboxes]
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    y = (height - total_h) / 2

    for i, line in enumerate(lines):
        bx0, by0, bx1, _ = bboxes[i]
        w = bx1 - bx0
        x = (width - w) / 2
        fill = colors["line_1"] if i == 0 else colors["line_2"]
        draw.text((x - bx0, y - by0), line, font=font, fill=hex_to_rgba(fill))
        y += heights[i] + line_gap

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)

    if args.manifest:
        manifest = {
            "asset": str(out),
            "title_lines": lines,
            "canvas": {"width": width, "height": height},
            "card": {
                "background": card["background"],
                "radius": radius,
                "padding_x": padding_x,
                "padding_y": padding_y,
            },
            "colors": colors,
            "font": {
                "family": font_cfg["family"],
                "resolved_path": str(font_path) if font_path else None,
                "fallback_used": font_path is None or font_cfg["family"] not in str(font_path),
                "size_px": getattr(font, "size", None),
            },
            "layout": {
                "split_line_y": canon["layout"]["split_line_y"],
                "center_x": title["position"]["center_x"],
                "center_y": title["position"]["center_y"],
            },
            "animation": title["animation"],
            "canon": {
                "file": str(Path(args.canon).resolve()),
                "version": canon["version"],
            },
        }
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render canonical Avatar Reel title card PNG.")
    parser.add_argument("--line1", required=True)
    parser.add_argument("--line2")
    parser.add_argument("--out", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--canon", default=str(DEFAULT_CANON))
    parser.add_argument("--font-path")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--radius", type=int)
    render(parser.parse_args())


if __name__ == "__main__":
    main()
