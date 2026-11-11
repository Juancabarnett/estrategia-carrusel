---
name: avatar-reel-editing
description: "Canonical post-production layer for Avatar Reel: title cards, split-layout captions, final audio/music/SFX mixing, and delivery QA. Owns the reusable visual/audio canon so the orchestrator doesn't rely on memory. Use for avatar_reel hook_visual, composite, captions and final stages."
---

# AVATAR-REEL-EDITING — canonical post-production

This is the reusable edit/post layer of `avatar_reel`. `avatar-reel` stays the orchestrator; this skill holds the operating canon for title, captions, final mix and QA.

Use it when the stage is `avatar_reel/hook_visual`, `composite`, `captions` or `final`, or whenever there's any doubt about position, colors, radius, animation, captions or music volume.

## Source of truth

Read **`references/avatar_reel_post_canon.json`** first. If an older instruction contradicts that file, the JSON wins. All colors/fonts in the canon are **neutral** — set them to your brand; the scripts read every value from the JSON, so editing it changes the output without touching code.

Bundled resources:

- `references/avatar_reel_post_canon.json` — hard values and expected sidecars.
- `scripts/render_title_card.py` — renders `title_card_reference_v2.png` with real radius.
- `scripts/build_avatar_reel_captions.py` — builds ASS/SRT/style/manifest from word timestamps + approved script text.
- `scripts/mix_avatar_reel_audio.py` — mixes voice + music with canonical ducking; premasters the voice to wav with single-pass dynamic loudnorm, measures integrated LUFS of premaster and final master, and fails if outside -17..-13 LUFS.
- `scripts/validate_avatar_reel_post.py` — mechanical checks before delivery.
- `templates/hyperframes_split_post/index.template.html` — HyperFrames base for animated title + captions.

## Quick contract

Default format:

- `1080x1920`, b-roll on top, avatar at the bottom.
- `split_line_y=1152`, b-roll `1080x1152` (60%), avatar `1080x768` (40%).
- The title plate crosses the split line. It doesn't float elsewhere unless the run documents another seam.

Title:

- max 2 lines and 6 words; card `1000x180`, radius `24`;
- colors and font are neutral defaults in the canon — change them to your brand;
- canonical asset per run: `title_card_reference_v2.png`; manifest: `title_card_manifest.json`;
- animation: slide+fade in, then fade/slide out.

Captions:

- uppercase, pure white, black outline; one visual line, max 3 words per chunk; no background box;
- `font_size ≈ 54px` at `1080x1920`;
- while the title is visible: `y=1000`; after the title: `y=1120`;
- timing from word timestamps reconciled to the final script, never raw ASR as final copy.

Audio:

- `music.mp3` is produced by `/music-ugc`; this skill mixes it;
- music default `0.08`, range `0.04-0.10`;
- real ducking with `sidechaincompress` against the voice (defaults `threshold=0.03`, `ratio=8`, `attack=12`, `release=300`), `amix=normalize=0`;
- voice up front, music as a subtle bed. If it competes with the voice, it's too loud.
- SFX: if the run has `sfx_plan.json`, mix each hit with `adelay` at the plan timestamp and per-hit gain (default `0.20`, range `0.10-0.30`). No sidechain — they're transients — but no hit may mask the start of a phrase. Record each hit in `final_mix_manifest.json.sfx[]`.

## Pipeline order

1. Lock the narrative before post. Produce a clean `video_composite.mp4` base in `1080x1920`.
2. Generate `title_card_reference_v2.png` with `scripts/render_title_card.py`.
3. Apply the animated title in HyperFrames or as an RGBA overlay. Don't use a rectangular ASS box for the plate.
4. Build captions from word timestamps and corrected copy. Don't use raw ASR as final text.
5. Burn captions at the end of the chain, after overlays, so they're not covered.
6. Mix audio with `scripts/mix_avatar_reel_audio.py` or an equivalent filter declared in `final_mix_manifest.json`.
7. Run visual/audio QA and save sidecars.

## Title

```bash
python3 .claude/skills/avatar-reel-editing/scripts/render_title_card.py \
  --line1 "YOUR HOOK" \
  --line2 "IN TWO LINES" \
  --out "$RUN_FOLDER/title_card_reference_v2.png" \
  --manifest "$RUN_FOLDER/title_card_manifest.json"
```

The manifest must record lines, resolved font, card width/height/radius, colors, `split_line_y` and the declared animation. To get a branded title, set `card.background`, `colors.line_1/line_2` and add a brand font path first in `title.font.paths` inside the canon JSON.

## Captions

Default: HyperFrames Smart Captions in an isolated `hyperframes_captions_project/`.

Canonical sync:

- transcribe `audio_final.mp3` (or the voice master) to word timestamps: `npx hyperframes@latest transcribe --model small --language <your-lang> --json`;
- use those timestamps **only** as timing;
- replace the text with the approved `script.txt` when word counts match;
- if counts don't match, allow auto-alignment only at high similarity and trace it in the manifest; on low confidence, stop and reconcile manually before burning;
- never use raw ASR as final copy if it has split tokens, broken proper nouns or invented words;
- build editorial chunks of 1-3 words, not word-by-word karaoke by default;
- terminal punctuation is a hard boundary: a `.`, `?` or `!` ends that caption. Never merge the end of one sentence with the start of the next.

```bash
python3 .claude/skills/avatar-reel-editing/scripts/build_avatar_reel_captions.py \
  --words "$RUN_FOLDER/captions.words.json" \
  --script "$RUN_FOLDER/script.txt" \
  --ass "$RUN_FOLDER/captions_canon.ass" \
  --srt "$RUN_FOLDER/captions.srt" \
  --style "$RUN_FOLDER/captions_style.json" \
  --manifest "$RUN_FOLDER/hyperframes_captions_manifest.json"
```

If the helper fails on low alignment confidence, that means reconciliation is missing — don't force it with raw ASR or guessed timing.

## Final mix

```bash
python3 .claude/skills/avatar-reel-editing/scripts/mix_avatar_reel_audio.py \
  --input "$RUN_FOLDER/composite_captioned.mp4" \
  --music "$RUN_FOLDER/music.mp3" \
  --out "$RUN_FOLDER/final.mp4" \
  --manifest "$RUN_FOLDER/final_mix_manifest.json"
```

If a run ships without music, mark it explicitly (`--allow-no-music`) and say so in the manifest. Music in spoken reels is a bed, not a co-lead: start at `music_volume=0.08`, drop to `0.04-0.06` if it masks consonants. QA must *listen* to hook, middle and close/CTA — not just read manifests.

## QA before delivery

```bash
python3 .claude/skills/avatar-reel-editing/scripts/validate_avatar_reel_post.py \
  --run-dir "$RUN_FOLDER" \
  --final "$RUN_FOLDER/final.mp4" \
  --require-title \
  --require-music
```

Beyond the script, check visually: a hook frame with the title visible, a post-title frame, audible music, and no black frames, cut text, captions over the avatar's face/hands, or title off the split line. QA is where a value written in the skill either shows up in the real video or doesn't.
