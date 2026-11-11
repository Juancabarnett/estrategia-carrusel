---
name: guion-ugc
description: "Generate spoken video scripts for short-form content: product UGC, news commentary, service explainers, opinion, tutorials, announcements. Adapts structure, tone, scene count and hook to the input. In avatar_reel it writes the spoken script the avatar will perform."
---

# GUION-UGC — spoken video script generator

You generate short-form video scripts adapted to any content type. In `avatar_reel`, you write the script the avatar speaks (`script.txt`, `script.md`, `script.json`). Pair this with **`/script-framework`** for the hook/retention lens.

## Output contract

In `avatar_reel`, write `script.txt`, `script.md` and/or `script.json` into the run folder, update `run.json` with the artifacts produced, and append the stage event to `logs/events.ndjson`. See [CONTRACT.md](../../../CONTRACT.md).

## Input: what the user gives you

A topic, a URL/article, a product photo, a service description, a trend, a screenshot/app, or an abstract concept. Identify the content type before scripting: **UGC product**, **UGC service**, **commentary/news**, **educational**, **entertainment**, or **announcement**.

## Decisions BEFORE scripting

### 1. Scene count — don't assume a number

- **4-5 scenes** — short, direct social messages.
- **6-8 scenes** — explainers, classic UGC, announcements.
- **8-12 scenes** — tutorials, longer stories, news with context.

**Key rule:** short lines per scene (max ~10-15 words). More scenes with short lines = more dynamic, more cuts. Better 10 scenes of 8 words than 5 scenes of 20.

### 2. Hook — first 1-2 seconds, always A/B

The hook is the only thing that decides watch-vs-scroll.

- The hook lives in the **first 1-2 seconds** (the first line). It must grab before the viewer realizes it's an ad.
- Combine a **visual** hook (what's in frame 1) and an **auditory** hook (the first line). One alone isn't enough.
- Produce **at least 2-3 hook variants** with different angles (e.g. pain-question vs counterintuitive statement). The user picks; the rest of the script doesn't change.
- Don't open linearly ("Hi, today I'll show you…"). Enter mid-action or with tension.
- If the user brings their own hook framework, it wins over this default.

Each variant declares: `id`, `line`, `visual` (frame 1), `angle`, `rationale`.

### 3. Duration by words-per-second (WPS)

Don't guess duration — compute it.

- Natural spoken pace ≈ **2.5 words/sec**; punchy UGC (after a TTS speed-up) ≈ **3.0-3.5 words/sec**.
- `scene_duration_s ≈ line_words / 3.0`, rounded up, floor ~1.5s per scene.
- Sum the scenes to estimate total duration and check it fits the target (typical short-form 20-35s). If it overflows, cut words — don't speed up until intelligibility breaks.
- Write `duration_seconds` per scene; downstream stages consume it.

### 4. Narrative structure (adapt to type)

- **UGC product:** Hook → Problem → Turn → Product → Benefit → CTA
- **Commentary/news:** Hook (the news) → Context → My take → Why it matters → Prediction → CTA
- **Explainer/service:** Hook (problem) → "Did you know…?" → What it is → How it works → Result → CTA
- **Educational:** Hook (question) → Simple concept → Example → Common mistake → Key tip → Close
- **Entertainment:** Setup → Build → Build → Punchline → Reaction → Tag
- **Announcement:** Teaser → Reveal → Features → Impact → Availability → CTA

### 5. Demos and source videos

When the input is a demo, screen recording or launch with audio/transcript, **don't write a description of the footage.**

- Transcribe/listen first; use the transcript to understand the news, the promise, the thesis.
- The script should sound like the speaker's own news/opinion piece, not "in this video we see…".
- Don't say "demo", "video", "B-roll", "here you can see", "appears", "clicks" unless the user wants an explicit tutorial.
- The visual is silent proof; the voice frames, translates and lands. If you can only explain the topic by narrating what's on screen, you haven't understood the source yet.

## Scripting process

### Spoken language, not written copy

The script is read aloud by a TTS and synced to a mouth. It must sound like a person talking, not ad copy.

- **Real fillers, in moderation** (one per scene max; don't caricature).
- **Pauses via punctuation**: use ellipses (…) for the beat before a turn, and full stops for cuts. The TTS reads punctuation as rhythm.
- **False starts / incomplete phrases** when they add naturalness.
- **Contractions and colloquial register** of the chosen accent/language.
- **Conversational rhythm**: alternate very short lines with the occasional medium one. Avoid perfect symmetry (sounds scripted).
- **Forbidden**: brochure jargon, feature lists, lines nobody would say in a voice note.

These marks are the raw material for the TTS Director's Notes (accent, pacing, emotion tags). Write the dialogue thinking about how it will *sound*.

### Scene plan (the canonical contract)

For each line, write a 2-3 sentence brief (what the character does, what's seen, gaze direction) and a structured `scene_plan[]` entry mapping **1:1 to the shots**:

- `scene`, `speaker`, `line`, `visible_character`, `off_camera`, `needs_lipsync`, `character_id`, `location_id`, `brief`, `emotion` (consumed by TTS for Director's Notes), `camera_motion`, `duration_seconds`.

Reality per scene: never leave it ambiguous who speaks. Never make a visible adult "speak" a line that belongs to a child voice. If the speaker is off-camera, the emotion still shows but don't force lipsync.

## Output (`script.json` shape)

```json
{
  "type": "commentary",
  "num_scenes": 8,
  "structure": "Hook → Context → Take → Importance → Prediction → CTA",
  "target_audience": "Short ICP summary for downstream stages.",
  "hook_variants": [
    { "id": "A", "line": "...", "visual": "frame 1", "angle": "pain-question", "rationale": "..." },
    { "id": "B", "line": "...", "visual": "frame 1", "angle": "counterintuitive", "rationale": "..." }
  ],
  "selected_hook": "A",
  "estimated_total_seconds": 26,
  "dialogues": ["line 1", "line 2"],
  "scene_briefs": ["brief 1", "brief 2"],
  "scene_plan": [
    {
      "scene": 1, "speaker": "host", "line": "line 1",
      "visible_character": "host", "off_camera": false, "needs_lipsync": true,
      "character_id": "host", "location_id": "main",
      "brief": "brief 1", "emotion": "direct, hook", "camera_motion": "locked off, slight drift",
      "duration_seconds": 3.5
    }
  ],
  "tts_notes": { "voice": "<Gemini voice>", "pacing": "Fast and punchy throughout", "accent": "<your accent/language>" }
}
```

For avatar reels there is usually one visible speaker (the user's avatar) talking to camera. Keep `location_id` simple and the gaze on camera.
