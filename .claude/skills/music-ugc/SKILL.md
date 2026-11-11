---
name: music-ugc
description: "Generate instrumental background music for short-form videos and avatar reels using Suno via the Kie.ai API. Creates a track that matches the mood and emotional curve of the reel. Use after the voice/video are locked and before the final mix. Always instrumental."
---

# MUSIC-UGC — instrumental background music

You generate an instrumental background track using Suno via the Kie.ai API. The music must complement the voice without competing with it.

## Contractual coverage

- `avatar_reel/music` is covered here. The canonical output is `music.mp3`.
- `music_prompt.json` and `music_task.json` are operational metadata for the stage.

## API

```
POST https://api.kie.ai/api/v1/generate
Authorization: Bearer {KIE_API_KEY}
Content-Type: application/json
```

**API key**: never hardcode. Read from env `KIE_API_KEY` (or `SUNO_KIE_API_KEY` as a fallback). If missing, stop the stage and ask the user — don't embed secrets.

## When it runs

After the locked voice/video and before the final mix:

```
... → voice / avatar render → MUSIC (instrumental) → final mix (voice + music)
```

## Request

```json
{
  "model": "V4_5PLUS",
  "title": "Reel background - <topic>",
  "style": "<genre/style matching the mood>",
  "prompt": "<mood, energy, instrumentation, emotional curve>",
  "instrumental": true,
  "customMode": true,
  "negativeTags": "<things to avoid, e.g. Aggressive, Dark, Vocals>"
}
```

**Always `"instrumental": true`** — no vocals competing with the spoken track.

## How to build the music prompt

Derive it from the script and the reel's emotional progression — not from a generic table. The music follows the same curve as the dialogue (e.g. tension → curiosity → resolution).

Template:

```
{intro_instruments} intro that feels {intro_emotion}.
Around 10-15 seconds in, {transition} as the energy shifts to {mid_emotion}.
Builds momentum with {build_instruments} reaching a {final_emotion} peak.
{tempo}. {overall_atmosphere}. No vocals, no lyrics.
```

- **Tempo:** fast for energy (110+ BPM), medium for transformation (90-100 BPM), slow for intimacy (70-85 BPM).
- **Instruments:** coherent with the topic and mood.

### Generic example

```json
{
  "model": "V4_5PLUS",
  "title": "Reel background - tool reaction",
  "style": "Lo-fi, Uplifting",
  "prompt": "Soft muted piano and gentle lo-fi drums intro that feels contemplative. Around 12 seconds in, a warm synth enters as the energy shifts to hopeful and curious. Builds with an uplifting pad and a groovy bassline reaching a bright, feel-good peak. Medium tempo, 95 BPM. Warm, modern atmosphere. No vocals, no lyrics.",
  "instrumental": true,
  "customMode": true,
  "negativeTags": "Heavy Metal, Aggressive, Dark, Vocals"
}
```

## Duration

The track should be **equal to or slightly longer** than the total video duration (~30-45s for a typical reel). Suno generates ~30s by default; loop/extend if needed.

## Polling

```
// response contains taskId
GET https://api.kie.ai/api/v1/task/{taskId}
Authorization: Bearer {KIE_API_KEY}
// when complete: response contains audioUrl to download as music.mp3
```

> Some Kie.ai download URLs (e.g. on tempfile hosts) return 403 without a `User-Agent` header. If the download fails, retry with a normal `User-Agent`.

## Mixing

The actual mix is done by `/avatar-reel-editing` in the `final` stage with real ducking (`scripts/mix_avatar_reel_audio.py`). Music is a **subtle bed** — start around 4-8% effective volume for spoken reels, not 15-20%.

### Intelligibility rule

- The voice always wins.
- A fixed low volume isn't enough — apply real ducking/sidechain against the voice.
- If an important word loses clarity, the mix is wrong even if it "sounds nice". When in doubt, choose the more sober mix.

## Pricing

~12 credits per generation; generates 2 variants per request.
