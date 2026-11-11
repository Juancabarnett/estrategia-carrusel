#!/usr/bin/env python3
"""sfx_lib.py — search, register and list SFX in the shared sfx/ library.

Subcommands:
  search <query>            search sfx/library.json (id, description, use_for, category)
  catalog <query> [--limit] search the HeyGen sound catalog (heygen audio sounds list)
  add ...                   download + process with the signature chain + register in library.json
  list                      list the full library (id, category, duration)

The library lives at <project-root>/sfx/. This script resolves it relative to its own
location, so keep the .claude/skills/sfx-ugc/scripts/ path intact and the sfx/ folder at
the project root.
"""
import argparse, datetime, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # project root (where sfx/ lives)
LIB_DIR = ROOT / "sfx"
MANIFEST = LIB_DIR / "library.json"

# Processing chains give every SFX a consistent "house" timbre. Tune the pitch/highpass
# to taste — these are neutral defaults, not tied to any brand.
CHAINS = {
    "pitched": "aresample=48000,asetrate=48000*0.94,aresample=48000,atempo=1.06383,highpass=f=80",
    "impact": "aresample=48000,asetrate=48000*0.92,aresample=48000,atempo=1.08696,highpass=f=35",
    "natural": "aresample=48000,highpass=f=70",
    "riser": "aresample=48000,highpass=f=50",
}
PROC_NAMES = {"pitched": "pitched_v1", "impact": "impact_v1",
              "natural": "natural_v1", "riser": "riser_v1"}


def load_manifest():
    return json.loads(MANIFEST.read_text())


def save_manifest(data):
    data["updated"] = datetime.date.today().isoformat()
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def cmd_search(args):
    words = [w for w in re.split(r"\W+", args.query.lower()) if w]
    rows = []
    for e in load_manifest()["sfx"]:
        haystack = " ".join([e["id"], e["category"], e["description"],
                             e.get("editorial_note", ""), " ".join(e["use_for"]),
                             " ".join(e["design_systems"])]).lower()
        score = sum(1 for w in words if w in haystack)
        if score:
            rows.append((score, e))
    rows.sort(key=lambda r: -r[0])
    for score, e in rows[: args.limit]:
        print(json.dumps({"score": score, "id": e["id"], "file": e["file"],
                          "duration_s": e["duration_s"], "use_for": e["use_for"],
                          "design_systems": e["design_systems"]}, ensure_ascii=False))
    if not rows:
        print("(sin matches en la librería — buscá en el catálogo con: sfx_lib.py catalog '<query>')",
              file=sys.stderr)
        sys.exit(1)


def cmd_catalog(args):
    out = subprocess.run(
        ["heygen", "audio", "sounds", "list", "--type", "sound_effects",
         "--query", args.query, "--limit", str(args.limit), "--min-score", str(args.min_score)],
        capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(out.stderr.strip() or "heygen CLI falló")
    for r in json.loads(out.stdout).get("data", []):
        print(json.dumps({"heygen_id": r["id"], "name": r["name"], "duration": r["duration"],
                          "score": round(r["score"], 2), "audio_url": r["audio_url"],
                          "description": r["description"][:160]}, ensure_ascii=False))


def cmd_add(args):
    data = load_manifest()
    if any(e["id"] == args.slug for e in data["sfx"]):
        sys.exit(f"ya existe '{args.slug}' en la librería — reusalo en vez de duplicar")
    relpath = f"{args.category}/{args.slug.removeprefix(args.category + '-')}.mp3"
    dest = LIB_DIR / relpath
    dest.parent.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw.mp3"
        stage = Path(td) / "stage.wav"
        subprocess.run(["curl", "-fsSL", args.url, "-o", str(raw)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
                        "-af", CHAINS[args.klass], str(stage)], check=True)
        probe = subprocess.run(["ffmpeg", "-i", str(stage), "-af", "volumedetect", "-f", "null", "-"],
                               capture_output=True, text=True).stderr
        m = re.search(r"max_volume: (-?[\d.]+) dB", probe)
        gain = round(-3.0 - float(m.group(1)), 2) if m else 0.0
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(stage),
                        "-af", f"volume={gain}dB,afade=t=in:d=0.005,areverse,afade=t=in:d=0.04,areverse",
                        "-codec:a", "libmp3lame", "-b:a", "192k", str(dest)], check=True)

    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                         "format=duration", "-of", "csv=p=0", str(dest)]).strip())
    entry = {
        "id": args.slug, "file": relpath, "category": args.category,
        "description": args.description,
        "use_for": [s.strip() for s in args.use_for.split(",")],
        "design_systems": [s.strip() for s in args.design_systems.split(",")],
        "editorial_note": args.note, "duration_s": round(dur, 2),
        "processing": PROC_NAMES[args.klass],
        "source": {"provider": args.provider, "heygen_id": args.heygen_id, "heygen_name": args.name},
        "added": datetime.date.today().isoformat(),
    }
    data["sfx"].append(entry)
    save_manifest(data)
    print(json.dumps(entry, ensure_ascii=False, indent=2))


def cmd_list(_):
    for e in load_manifest()["sfx"]:
        print(f"{e['id']:28} {e['duration_s']:>6}s  {', '.join(e['design_systems'])}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--limit", type=int, default=8)
    s.set_defaults(fn=cmd_search)

    c = sub.add_parser("catalog"); c.add_argument("query")
    c.add_argument("--limit", type=int, default=5); c.add_argument("--min-score", type=float, default=0.55)
    c.set_defaults(fn=cmd_catalog)

    a = sub.add_parser("add")
    a.add_argument("--slug", required=True, help="id único, ej. whoosh-metal-flick")
    a.add_argument("--category", required=True,
                   choices=["whoosh", "impact", "paper", "glass", "ui", "arcade", "riser", "sparkle", "foley", "ambient"])
    a.add_argument("--class", dest="klass", required=True, choices=list(CHAINS))
    a.add_argument("--url", required=True, help="audio_url pre-firmada del catálogo (expira: descargar ya)")
    a.add_argument("--description", required=True)
    a.add_argument("--use-for", required=True, help="lista separada por comas")
    a.add_argument("--design-systems", default="any", help="comma-separated tags for your own visual systems, e.g. editorial,glass_ui,pixel_insert,any")
    a.add_argument("--note", default="")
    a.add_argument("--heygen-id", default=None)
    a.add_argument("--name", default=None)
    a.add_argument("--provider", default="heygen_catalog")
    a.set_defaults(fn=cmd_add)

    l = sub.add_parser("list"); l.set_defaults(fn=cmd_list)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
