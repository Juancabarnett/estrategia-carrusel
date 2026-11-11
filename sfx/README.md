# SFX — shared sound-effects library

A library **shared across all flows** (avatar_reel, etc.). The rule is **reuse before generating**: every SFX downloaded/processed in a run enters here and stays available for the next.

> **Owner skill: `/sfx-ugc`** (`.claude/skills/sfx-ugc/`). Its helper `scripts/sfx_lib.py` automates search, registration and indexing.

> **What ships in this pack:** `library.json` is an *index* of pointers to the HeyGen sound catalog (by id) plus the processing recipe. The actual `.mp3` files are **not** included — re-fetch and process them with `sfx_lib.py add`, or build your own library.

## How to search

```bash
# 1. ALWAYS the local library first
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py search "whoosh transition"

# 2. If no match, the HeyGen catalog (semantic, CLI >= v0.1.1)
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py catalog "whoosh for a scene change" --limit 5
```

The catalog returns semantically ranked results with a pre-signed `audio_url` (**expires in 7 days**: download now, never store the URL as an asset).

## How to register a new SFX

1. Download the `audio_url` to a temp file.
2. Process with the signature chain (see `signature_processing` in `library.json`): resample 48k → highpass → subtle pitch per class → peak-normalize to -3 dBFS → anti-click fades (5ms in / 40ms out) → mp3 192k.
   - `pitched_v1` (~ -1 semitone): whoosh, glass, ui, pop, sparkle.
   - `impact_v1` (~ -1.4 semitones): impacts/thuds, more weight.
   - `natural_v1` (no pitch): iconic sounds that shouldn't be retuned — paper, arcade 8-bit, foley.
   - `riser_v1` (no pitch): risers.
3. Save to `sfx/<category>/<slug>.mp3` and **register the entry in `library.json`** (id, file, use_for, design_systems, duration_s, processing, source.heygen_id).

`sfx_lib.py add` does all three steps.

## Categories

| Folder | For |
|---|---|
| `whoosh/` | transitions, b-roll cuts, card entries |
| `impact/` | title-card landings, strong statements, hard data |
| `paper/` | editorial / paper-canvas looks |
| `glass/` | glass / UI looks (widgets, cards) |
| `ui/` | clicks, pings, pops, demos |
| `arcade/` | pixel/arcade inserts (8-bit, no pitch) |
| `riser/` | tension builds toward a rehook/CTA |
| `sparkle/` | reveals, "wow" moments |
| `foley/` | cash register, camera shutter, typing |

The **when and how much** to use SFX in an avatar reel lives in `.claude/skills/avatar-reel/SKILL.md` (SFX section); the mix levels live in `.claude/skills/avatar-reel-editing/references/avatar_reel_post_canon.json` (`audio.sfx`).
