#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CANON = SKILL_DIR / "references" / "avatar_reel_post_canon.json"

WORD_RE = re.compile(r"[¿¡]?(?:[0-9]+(?:\.[0-9]+)?|[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)[.,;:!?]?", re.UNICODE)
TERMINAL_PUNCTUATION_DEFAULT = [".", "?", "!"]
# Chunking rules (user feedback 2026-06-10): ALL punctuation — terminal and clause
# marks — closes its chunk; a caption never shows text from both sides of a comma/colon.
CHUNK_PUNCTUATION = ".?!…,:;"
TRAILING_QUOTES = "”\"'’"
GLUE_NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def load_canon(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_token(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def script_words(script: str) -> list[str]:
    return [normalize_token(m.group(0)) for m in WORD_RE.finditer(script)]


def norm_for_align(text: str) -> str:
    return re.sub(r"[^0-9a-záéíóúüñ]+", "", text.lower())


def load_words(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = data.get("words") or data.get("transcript") or data.get("segments") or []
    else:
        raise ValueError("Unsupported words JSON shape")

    words: list[dict[str, Any]] = []
    for item in raw:
        text = item.get("text", item.get("word", ""))
        start = item.get("start")
        end = item.get("end")
        if text is None or start is None or end is None:
            continue
        text = normalize_token(str(text))
        if not text:
            continue
        words.append({"text": text, "start": float(start), "end": float(end)})
    return words


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    hh, rem = divmod(cs, 360_000)
    mm, rem = divmod(rem, 6_000)
    ss, cc = divmod(rem, 100)
    return f"{hh:d}:{mm:02d}:{ss:02d}.{cc:02d}"


def srt_time(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    hh, rem = divmod(ms, 3_600_000)
    mm, rem = divmod(rem, 60_000)
    ss, ms = divmod(rem, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "").replace("}", "")


def upper_clean(text: str) -> str:
    fixes = {
        "GP T": "GPT",
        "CODE X": "CODEX",
        "MID JOURNEY": "MIDJOURNEY",
        "M ID JOURNEY": "MIDJOURNEY",
        "L OR A": "LORA",
        "L OR AS": "LORAS",
        "IM Á GENES": "IMÁGENES",
    }
    out = re.sub(r"\s+", " ", text.strip()).upper()
    for old, new in fixes.items():
        out = out.replace(old, new)
    return out


def terminal_marks_from_canon(canon: dict[str, Any]) -> list[str]:
    sync = canon.get("captions", {}).get("sync", {})
    marks = sync.get("terminal_punctuation_marks", TERMINAL_PUNCTUATION_DEFAULT)
    return [str(mark) for mark in marks if str(mark)]


def unit_closes_chunk(text: str) -> bool:
    stripped = text.rstrip(TRAILING_QUOTES)
    return bool(stripped) and stripped[-1] in CHUNK_PUNCTUATION


def is_glued_name(prev_text: str, next_text: str) -> bool:
    # Multi-word names (PLAN A, FABLE 5, OPUS 4.8) count as ONE visual unit.
    if unit_closes_chunk(prev_text):
        return False
    core = next_text.strip(".,:;?!…¿¡" + TRAILING_QUOTES)
    if GLUE_NUMBER_RE.fullmatch(core):
        return True
    return len(core) == 1 and core.isalpha() and core.isupper()


def glue_name_units(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    i = 0
    while i < len(words):
        unit = dict(words[i])
        if i + 1 < len(words) and is_glued_name(unit["text"], words[i + 1]["text"]):
            nxt = words[i + 1]
            unit = {"text": unit["text"] + " " + nxt["text"], "start": unit["start"], "end": nxt["end"]}
            i += 1
        units.append(unit)
        i += 1
    return units


def split_sizes(n: int, max_units: int) -> list[int]:
    # Balance chunk sizes inside a clause so no 1-unit orphan appears unless the
    # clause itself is a single unit ("DESLIZÁS,").
    if n <= max_units:
        return [n] if n else []
    best: list[int] | None = None
    for first in range(max_units, 1, -1):
        rest = split_sizes(n - first, max_units)
        candidate = [first] + rest
        if 1 not in candidate:
            return candidate
        if best is None:
            best = candidate
    return best


def suspicious_raw_text(text: str) -> bool:
    upper = text.upper()
    if re.search(r"\b[A-ZÁÉÍÓÚÑ]\s+[A-ZÁÉÍÓÚÑ]{1,3}\b", upper):
        return True
    bad = ["GP T", "CODE X", "M ID", "IM Á", "L OR", "SAL IÓ", "PENS ADO"]
    return any(fragment in upper for fragment in bad)


def interpolate_script_words(script_slice: list[str], timing_slice: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not script_slice:
        return []
    if not timing_slice:
        raise ValueError(f"Script words without timing: {' '.join(script_slice)}")

    span_start = timing_slice[0]["start"]
    span_end = timing_slice[-1]["end"]
    if len(script_slice) == 1:
        return [{"text": script_slice[0], "start": span_start, "end": span_end}]
    if len(script_slice) == len(timing_slice):
        return [{**timing, "text": text} for timing, text in zip(timing_slice, script_slice)]

    weights = [max(1, len(norm_for_align(word))) for word in script_slice]
    total = sum(weights)
    cursor = span_start
    out: list[dict[str, Any]] = []
    for i, (word, weight) in enumerate(zip(script_slice, weights)):
        if i == len(script_slice) - 1:
            end = span_end
        else:
            end = span_start + (span_end - span_start) * (sum(weights[: i + 1]) / total)
        out.append({"text": word, "start": cursor, "end": max(end, cursor + 0.05)})
        cursor = end
    return out


def align_script_to_timings(script_tokens: list[str], words: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    script_norm = [norm_for_align(token) for token in script_tokens]
    timing_norm = [norm_for_align(word["text"]) for word in words]
    matcher = difflib.SequenceMatcher(None, script_norm, timing_norm, autojunk=False)
    aligned: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        script_slice = script_tokens[i1:i2]
        timing_slice = words[j1:j2]
        if tag == "equal":
            aligned.extend({**timing, "text": text} for timing, text in zip(timing_slice, script_slice))
            continue
        if tag == "insert":
            changes.append({"op": tag, "dropped_timing_text": [w["text"] for w in timing_slice], "timing_range": [j1, j2]})
            continue
        changes.append(
            {
                "op": tag,
                "script_text": script_slice,
                "timing_text": [w["text"] for w in timing_slice],
                "script_range": [i1, i2],
                "timing_range": [j1, j2],
            }
        )
        if tag in {"replace", "delete"}:
            aligned.extend(interpolate_script_words(script_slice, timing_slice))

    return aligned, changes, matcher.ratio()


def reconcile_words(words: list[dict[str, Any]], script_path: Path | None, allow_raw_text: bool) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]], float | None]:
    if script_path:
        approved = script_words(script_path.read_text(encoding="utf-8"))
        if len(approved) != len(words):
            aligned, changes, ratio = align_script_to_timings(approved, words)
            if ratio < 0.88:
                raise ValueError(
                    f"script/timing word count mismatch and low alignment confidence: script has {len(approved)} words, "
                    f"timestamps have {len(words)}, ratio={ratio:.3f}. Manually reconcile before burning captions."
                )
            return aligned, "script_text_auto_aligned_to_word_timestamps", changes, ratio
        reconciled = [{**timing, "text": text} for timing, text in zip(words, approved)]
        return reconciled, "script_text_replaced_asr_with_equal_word_count", [], 1.0

    joined = " ".join(w["text"] for w in words[:80])
    if suspicious_raw_text(joined) and not allow_raw_text:
        raise ValueError("Raw ASR appears to contain split-token artifacts. Provide --script or pass --allow-raw-text explicitly.")
    return words, "raw_words_used_no_script", [], None


def group_words(words: list[dict[str, Any]], canon: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = canon["captions"]
    sync = cfg["sync"]
    max_units = int(cfg["max_words_per_caption"])

    units = glue_name_units(words)
    clauses: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for unit in units:
        current.append(unit)
        if unit_closes_chunk(unit["text"]):
            clauses.append(current)
            current = []
    if current:
        clauses.append(current)

    groups: list[list[dict[str, Any]]] = []
    for clause in clauses:
        pos = 0
        for size in split_sizes(len(clause), max_units):
            groups.append(clause[pos : pos + size])
            pos += size

    for group in groups:
        for unit in group[:-1]:
            if unit_closes_chunk(unit["text"]):
                raise ValueError(
                    "Caption chunk crosses punctuation: "
                    + " ".join(u["text"] for u in group)
                )

    events: list[dict[str, Any]] = []
    lead = float(sync["event_start_lead_s"])
    tail_default = float(sync["event_tail_s"])
    tail_punct = float(sync["event_tail_punctuation_s"])
    min_duration = float(sync["min_event_duration_s"])
    title_until = float(canon["title"]["visible_until_s_default"])

    for i, group in enumerate(groups):
        raw_start = group[0]["start"]
        raw_end = group[-1]["end"]
        text = upper_clean(" ".join(w["text"] for w in group))
        tail = tail_punct if re.search(r"[.,;:!?]$", group[-1]["text"]) else tail_default
        start = max(0.0, raw_start - lead)
        end = max(raw_end + tail, start + min_duration)
        if i + 1 < len(groups):
            next_start = max(0.0, groups[i + 1][0]["start"] - lead)
            if end >= next_start:
                # No overlap is stricter than minimum duration; short function-word chunks
                # can be visually brief, but two captions must never be active together.
                end = max(start + 0.05, next_start - 0.018)
        y = cfg["title_active_y"] if start < title_until else cfg["default_y"]
        events.append({"start": round(start, 3), "end": round(end, 3), "raw_end": round(raw_end, 3), "text": text, "y": y, "word_count": len(group)})
    return events


def write_ass(path: Path, events: list[dict[str, Any]], canon: dict[str, Any]) -> None:
    cfg = canon["captions"]
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{cfg['font_family']},{cfg['font_size_px']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{cfg['outline_width_px']},0,2,80,80,80,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for event in events:
        lines.append(
            f"Dialogue: 0,{ass_time(event['start'])},{ass_time(event['end'])},Default,,0,0,0,,"
            f"{{\\an2\\pos(540,{event['y']})}}{escape_ass(event['text'])}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_srt(path: Path, events: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for i, event in enumerate(events, 1):
        lines.extend([str(i), f"{srt_time(event['start'])} --> {srt_time(event['end'])}", event["text"], ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build canonical Avatar Reel captions from word timings plus approved script text.")
    parser.add_argument("--words", required=True, help="captions.words.json with word/text start/end.")
    parser.add_argument("--script", help="Approved script.txt. Required for final copy unless raw text is explicitly allowed.")
    parser.add_argument("--ass", required=True)
    parser.add_argument("--srt", required=True)
    parser.add_argument("--style", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--canon", default=str(DEFAULT_CANON))
    parser.add_argument("--allow-raw-text", action="store_true")
    args = parser.parse_args()

    canon = load_canon(Path(args.canon))
    words = load_words(Path(args.words))
    reconciled, method, changes, ratio = reconcile_words(words, Path(args.script) if args.script else None, args.allow_raw_text)
    events = group_words(reconciled, canon)

    write_ass(Path(args.ass), events, canon)
    write_srt(Path(args.srt), events)

    style = {
        "component": canon["captions"]["component"],
        "provider": "hyperframes_smart_captions_timing_with_ffmpeg_burn_in",
        "placement": "above_avatar_split_on_broll",
        "case": canon["captions"]["case"],
        "color": canon["captions"]["color"],
        "accent_color": None,
        "outline_color": canon["captions"]["outline_color"],
        "outline_width_px": canon["captions"]["outline_width_px"],
        "font_family": canon["captions"]["font_family"],
        "font_size_px": canon["captions"]["font_size_px"],
        "max_words_per_caption": canon["captions"]["max_words_per_caption"],
        "single_line": canon["captions"]["single_line"],
        "background": canon["captions"]["background"],
        "title_active_y": canon["captions"]["title_active_y"],
        "default_y": canon["captions"]["default_y"],
        "split_line_y": canon["captions"]["split_line_y"],
        "source_text": str(args.script) if args.script else "raw_words_explicitly_allowed",
        "timing_source": str(args.words),
        "sync_method": method,
        "alignment_ratio": ratio,
        "alignment_changes_count": len(changes),
        "title_visible_until_s": canon["title"]["visible_until_s_default"],
        "terminal_punctuation_hard_boundary": canon["captions"]["sync"].get("terminal_punctuation_hard_boundary", True),
        "terminal_punctuation_marks": terminal_marks_from_canon(canon),
        "forbid_cross_sentence_caption_chunks": canon["captions"]["sync"].get("forbid_cross_sentence_caption_chunks", True),
    }
    Path(args.style).write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "version": 1,
        "method": "word_timing_plus_approved_script_text_avatar_reel_chunks",
        "words_path": str(args.words),
        "script_path": str(args.script) if args.script else None,
        "ass_path": str(args.ass),
        "srt_path": str(args.srt),
        "style_path": str(args.style),
        "events_count": len(events),
        "chunking": {
            "method": "punctuation_respecting_v2",
            "rules": "all punctuation (. ? ! , : ;) closes its chunk; max "
            + str(canon["captions"]["max_words_per_caption"])
            + " visual units per chunk; multi-word names (PLAN A, FABLE 5, OPUS 4.8) glued as one unit; "
            "sizes balanced per clause to avoid 1-word orphans",
        },
        "sync": canon["captions"]["sync"],
        "sentence_boundary_policy": {
            "terminal_punctuation_hard_boundary": canon["captions"]["sync"].get("terminal_punctuation_hard_boundary", True),
            "terminal_punctuation_marks": terminal_marks_from_canon(canon),
            "forbid_cross_sentence_caption_chunks": canon["captions"]["sync"].get("forbid_cross_sentence_caption_chunks", True),
        },
        "alignment_ratio": ratio,
        "alignment_changes": changes[:80],
        "events": events,
        "canon": {"file": str(Path(args.canon).resolve()), "version": canon["version"]},
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
