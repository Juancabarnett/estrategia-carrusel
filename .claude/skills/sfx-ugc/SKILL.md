---
name: sfx-ugc
description: "Pointed sound design for any flow or video: search, register and mix sound effects from the shared sfx/ library (library-first) or the HeyGen sound catalog. Use whenever a video needs SFX hits anchored to visual events, or to register a new SFX in the library."
---

# SFX-UGC — pointed sound design

A cross-flow skill: any pipeline can call it (avatar_reel uses it in its `sfx` stage), or the user can call it directly on a standalone video. It owns the search → register → plan → mix workflow over the shared `sfx/` library.

## Output contract

- The reusable library is **`sfx/` at the project root** (`sfx/library.json` + `sfx/<category>/<slug>.mp3`), shared across all flows.
- A run **copies** the SFX it uses into `<run>/sfx/` and references their origin in `sfx_plan.json`. A useful SFX never lives only inside a run.

> **About this pack:** the shipped `sfx/library.json` is an *index* of pointers to the HeyGen sound catalog (by id) — the `.mp3` files are NOT included. Re-fetch and process them with `sfx_lib.py add` (needs the HeyGen CLI), or build your own library from scratch.

## Data Nube default: every reel gets SFX

Include sound effects in every reel unless the user says not to. Source them in this order:

1. The shared `sfx/` library.
2. **Openverse** real recordings: `/openverse`, with `scripts/openverse_sound.py`. Copy `creditos_sonido.txt` to the run and remind the user to paste CC BY credits in the description.
3. **Earshot** v0.4.1 (`github.com/Leonxlnx/earshot`), with its bank of 252 sounds, through the project launcher: `scripts\earshot.cmd sfx list`, `scripts\earshot.cmd sfx render ID -o x.wav --sr 48000`, `scripts\earshot.cmd sfx check x.wav`. The code is in `tools/earshot/`. Place a sound so its `peak s` value from `sfx list` lands on the visual event. The PyPI package named `earshot` is a different project.

This copy runs only the bank commands (`sfx`, `kit`, `measure`). The listening commands (`describe`, `critique`, `timeline`) need PyTorch and about 1.1 GB of models, which are not installed, so the agent still can't hear the mix: tell the user to listen to it.

## Tool

`scripts/sfx_lib.py` (python3, needs ffmpeg + HeyGen CLI ≥ v0.1.1):

```bash
# 1. ALWAYS first: search the shared library
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py search "whoosh transition title card"

# 2. If no match: search the HeyGen catalog (semantic, in English)
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py catalog "soft airy whoosh transition" --limit 5

# 3. Register (download + signature processing + record in library.json)
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py add \
  --slug whoosh-metal-flick --category whoosh --class pitched \
  --url "<audio_url from the catalog>" \
  --description "..." --use-for "fast cut,flick" --design-systems any \
  --heygen-id <id> --name "<catalog name>"

# Full inventory
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py list
```

- The catalog `audio_url` is pre-signed and **expires in 7 days**: download immediately, never store the URL as an asset.
- `--class` picks the processing signature: `pitched` (~ -1 semitone — whoosh/glass/ui/pop/sparkle), `impact` (~ -1.4, more weight), `natural` (iconic: paper/arcade/foley — untouched), `riser`.
- `add` fails if the slug exists — on purpose: reuse instead of duplicating.

## Hard rules

1. **Library-first**: never download a sound without running `search` first. A "close enough" in the library beats a new download.
2. **Every new SFX enters the library**, not the run: the run copies from `sfx/` into `<run>/sfx/`.
3. **Anchor to visual events**, never to words or captions: card in/out, edit cuts, reveals, inserts, freezes, CTA. If you can't name the visual event, the SFX doesn't go.
4. **Anti-abuse budget**: 4-8 hits per 30s, max 1 per beat (the hook/opener allows 2: whoosh + thud), ≥2s apart, never two identical hits in a row.
5. **The voice wins**: no hit may mask the start of a phrase. If it does, lower it or move it to the nearest visual cut.

## Plan & mix

1. Write `sfx_plan.json` at the work destination: `{ "design_system": ..., "events": [{ "t": <s>, "sfx_id": ..., "file": ..., "anchor": "<visual event>", "gain": 0.20, "reason": ... }] }`. `anchor` names the visual event (e.g. `title_card_in`, `broll_cut_beat_3`).
2. Copy the used files into `<dest>/sfx/`.
3. Mix each hit with `adelay` at the timestamp + `amix=normalize=0`; default gain `0.20`, range `0.10-0.30`. No sidechain (transients). FFmpeg pattern:

```bash
ffmpeg -i video.mp4 -i sfx/airy-soft.mp3 -i sfx/bass-title.mp3 -filter_complex \
  "[1:a]adelay=350|350,volume=0.20[s1];[2:a]adelay=600|600,volume=0.18[s2];\
   [0:a][s1][s2]amix=inputs=3:duration=first:normalize=0[aout]" \
  -map 0:v -map "[aout]" -c:v copy out.mp4
```

4. QA: listen to (or analyze the waveform at) each anchor — the hit must land on the visual event and the first word of the next phrase must stay clean. Record hits in `final_mix_manifest.json.sfx[]` when the flow has a mix manifest.

## Per-flow integration

- **avatar_reel**: the `sfx` stage uses this skill for sourcing/plan; the mix runs in `final` via `/avatar-reel-editing` using the `audio.sfx` canon in `avatar_reel_post_canon.json` (which wins on conflict).
- **Standalone video**: apply the FFmpeg pattern above directly.

## Design-system palette (define your own)

Map SFX families to **your** visual systems via the `design_systems` tag on each library entry (`any` works everywhere). For example you might map an editorial/paper look to page-turn and camera-shutter sounds, a glass/UI look to pings and pops, and a pixel/arcade insert to 8-bit chimes. The pack ships neutral tags — rename them to your systems.
