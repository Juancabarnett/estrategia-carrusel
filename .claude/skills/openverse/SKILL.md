---
name: openverse
description: "Find open-licence sound effects, audio and photos on Openverse for a reel, download them and record their credits. Use when a video needs SFX, sounds or images related to what is said. Needs no API key."
---

# Openverse

Find sound effects, audio and real photos with Openverse. It needs no API key and no account.

## Sound

```bash
python3 .claude/skills/openverse/scripts/openverse_sound.py "whoosh" --out "$RUN_FOLDER/sfx" --limit 3 --max-seconds 4
```

Each search saves in `--out`:

- the sounds, named after the query
- `openverse_sound_credits.json`, the source data
- `creditos_sonido.txt`, text ready for the post description

Use short English terms: `whoosh`, `cash register`, `pop`, `click`, `coin`, `paper`. For longer audio, raise the limits and try `--category music --min-seconds 40 --max-seconds 240`. Openverse has few business tracks, so reel music normally comes from `/music-ugc`.

Place effects on visual events, never on words, following `/sfx-ugc`: 4-8 hits per 30 s, at least 2 s apart, and the voice always wins. To reuse a sound later, register it in `sfx/library.json` with `sfx_lib.py`.

## Photos

```bash
python3 .claude/skills/openverse/scripts/openverse_search.py "small shop owner" --out "$RUN_FOLDER/tmp/candidatas" --limit 4
```

This saves the images, a contact sheet `_hoja_<query>.jpg`, `openverse_credits.json` and `creditos_openverse.txt`.

## Rules

- **Licences:** the default is `cc0,pdm,by`. Don't add `by-sa`, `by-nd` or `by-nc` without asking the user: those terms are hard to meet in an edited or commercial video.
- **Credits:** CC BY files require attribution. Copy the credits text to the run and remind the user to paste it in the description.
- **Approval:** show the user the chosen images before editing.
- **Check each file:** listen to every sound before using it. In photos, look for foreign brands, foreign currency, readable phone numbers or private data, and anything that doesn't match what is being said.
- **Logos:** Openverse is not for logos. Take them from an official source or Wikimedia Commons.
