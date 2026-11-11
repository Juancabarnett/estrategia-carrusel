---
name: tts-ugc
description: "Generate dialogue audio for short-form scenes and avatar reels with ElevenLabs Eleven v4 text to speech and the user's cloned voice. Gemini is not used. Handles loudness and final audio delivery."
---

# TTS-UGC — voice for scenes and avatar reels

You generate the spoken audio with **ElevenLabs Eleven v4 and the user's cloned voice**. Go straight to "ElevenLabs direct TTS" below. The user stopped using Gemini, so **never call Gemini TTS or speech-to-speech** unless the user asks to go back. The Gemini sections in this file are kept only as reference.

The speaker's voice canon lives in **`avatar-reel/identity.json → voice_generation_canon`**, emitted into the run by `identity_guard.py`. Use it as the default; the user defines their own profile there. **None of the values are prescriptive — they come from the user's identity file.**

## Contractual coverage

- `avatar_reel/tts` generates `audio_final.mp3` (+ `.wav`) with ElevenLabs. `preferred_voice_mode` is `elevenlabs_tts`: generate the whole script in one call with the settings in `voice_generation_canon.elevenlabs_tts` (see "ElevenLabs direct TTS").
- `avatar_reel/voice_change` is always `skipped`.

## Legacy Gemini workflow (not used)

Read `identity.json.voice_generation_canon` (via `identity_guard.json`). The general technique:

- **One Gemini TTS call per script segment / spoken line**, then concatenate the raw segments. Don't send the whole script in a single call for avatar reels — per-segment gives cleaner timing and direction.
- **Post-process** the concatenated raw: optional `atempo` speed-up (from the identity file; `1.0` = none), then `loudnorm=I=-16:TP=-1.5:LRA=11`. Export `audio_gemini.wav` and `audio_gemini.mp3`.
- Do **not** run aggressive `silenceremove` before concatenation — it has trimmed valid audio and produced broken masters. Clean borders conservatively, after validating duration.
- If `preferred_voice_mode` is `gemini_tts_elevenlabs`, convert the performance with ElevenLabs speech-to-speech to the cloned voice (see below). Gemini defines the performance; ElevenLabs only sets the final vocal identity.

## API

```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent?key={GEMINI_API_KEY}
Content-Type: application/json
```

## How to prompt Gemini TTS

The text you send in `contents.parts.text` is NOT just the dialogue. It's a **structured prompt** with 3 sections before the transcript:

```
Audio Profile: [Who the speaker is — identity, role, personality]

Scene: [Context — where they are, what's happening, mood]

Director's Notes:
- Style: [tone — confessional, enthusiastic, reflective]
- Accent: [specific accent / language and pronunciation notes]
- Pacing: [rhythm — fast at the start to grab, slower in emotional beats]
- Energy: [energy level for THIS scene]

Transcript:
[The dialogue with inline audio tags]
```

Derive the Director's Notes from the run's artifacts (the `voice_generation_canon`, the scene `emotion`, the script) — don't invent the performance. Keep the vocal identity and accent **identical across scenes**; only the emotion and contour change.

### Breathing, pauses and dynamic range (realism)

- **Pauses:** `…` for the beat before a turn; full stops to cut. The model reads punctuation as rhythm.
- **Breathing:** `[sighs]`, `[breath]` or a leading `…` sell naturalness. One per scene, no more.
- **Dynamic range:** the line isn't flat — it can drop in a confession and rise on the payoff without losing the fast pacing. Describe the contour in Energy.

### Generic example (replace with your own profile)

```
Audio Profile: A direct, curious creator talking to camera like a friend sending a voice note. Dry humor, no announcer polish.

Scene: Recording a quick reel about a tool they just tried. Casual, handheld energy.

Director's Notes:
- Style: Casual, observational, with a smile in the voice
- Accent: [your accent / language — be specific about pronunciation if it matters]
- Pacing: Fast and punchy from the first word; clear on the punchline
- Energy: Medium-high, amused and curious

Transcript:
[speaking quickly] Okay, this changes how I make videos.
```

### Audio tags (inline, always in English)

**Emotions:** `[excited]`, `[tired]`, `[frustrated]`, `[relieved]`, `[curious]`, `[amazed]`, `[sarcastic]`, `[serious]`, `[bored]`, `[reluctantly]`

**Sounds:** `[whispers]`, `[laughs]`, `[cough]`, `[sighs]`, `[gasp]`

**Speed:** `[very fast]`, `[very slowly]`, `[speaking quickly]`

**Creative:** `[singing]`, `[like announcing a winner]`, `[with a vocal smile]` — the model interprets creative tags freely.

**Pauses:** no tag — use ellipses (…) or full stops.

## Request body

```json
{
  "contents": [{ "parts": [{ "text": "Audio Profile: ...\n\nScene: ...\n\nDirector's Notes:\n- Style: ...\n\nTranscript:\n[curious] ..." }] }],
  "generationConfig": {
    "responseModalities": ["AUDIO"],
    "speechConfig": { "voiceConfig": { "prebuiltVoiceConfig": { "voiceName": "Puck" } } }
  }
}
```

**Do NOT use `systemInstruction`** — this model errors (400). All context goes in `text`.

## Voices (30)

| Voice | Character | Voice | Character |
|-----|----------|-----|----------|
| Zephyr | Bright | Algenib | Gravelly |
| Puck | Upbeat | Rasalgethi | Informative |
| Charon | Informative | Laomedeia | Upbeat |
| Kore | Firm | Achernar | Soft |
| Fenrir | Excitable | Alnilam | Firm |
| Leda | Youthful | Schedar | Even |
| Orus | Firm | Gacrux | Mature |
| Aoede | Breezy | Pulcherrima | Forward |
| Callirrhoe | Easy-going | Achird | Friendly |
| Autonoe | Bright | Zubenelgenubi | Casual |
| Enceladus | Breathy | Vindemiatrix | Gentle |
| Iapetus | Clear | Sadachbia | Lively |
| Umbriel | Easy-going | Sadaltager | Knowledgeable |
| Algieba | Smooth | Sulafat | Warm |
| Despina | Smooth | Erinome | Clear |

Tip: for natural, textured UGC voices, the casual/friendly options (e.g. Algenib, Zubenelgenubi, Enceladus, Achird) tend to read less like a radio announcer than the firm/informative ones. Pick one and keep it consistent.

## Output

- **Format:** PCM 16-bit signed, 24kHz, mono.
- **Location:** `response.candidates[0].content.parts[0].inlineData.data` (base64).
- **To WAV:** prepend a 44-byte RIFF/WAVE/fmt/data header.

## Multi-speaker (up to 2 in one clip)

```json
"speechConfig": {
  "multiSpeakerVoiceConfig": {
    "speakerVoiceConfigs": [
      { "speaker": "A", "voiceConfig": { "prebuiltVoiceConfig": { "voiceName": "Leda" } } },
      { "speaker": "B", "voiceConfig": { "prebuiltVoiceConfig": { "voiceName": "Aoede" } } }
    ]
  }
}
```

Use multi-speaker only when two speakers share the same audio clip. For an avatar reel there's usually one speaker — generate one voice per segment.

## Pacing rule — keep it fast

For UGC/short-form, Pacing should always include "Fast and punchy" or "Very fast", and speed tags (`[speaking quickly]`, `[very fast]`) belong in each transcript. Even "negative" scenes (frustration, tiredness) stay fast — the emotion changes, the speed doesn't. If the audio is slow, the viewer scrolls.

## ElevenLabs direct TTS

When `preferred_voice_mode` is `elevenlabs_tts`, the cloned voice speaks the script directly:

```
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_192
Header: xi-api-key: {ELEVENLABS_API_KEY}
Content-Type: application/json

Body: { "text": "...", "model_id": "eleven_v4", "language_code": "es", "voice_settings": { "stability": 0.4, "similarity_boost": 0.75 } }
```

- `eleven_v4` is text-to-speech only: it cannot do speech-to-speech, so never put it in `elevenlabs_sts.model_id`.
- v4 takes only `stability` and `similarity_boost`. It has no style or speed setting and no SSML.
- Send the full script in one call for continuous delivery, then apply `loudnorm=I=-16:TP=-1.5:LRA=11` and trim edges to under ~120ms of silence.

## ElevenLabs voice change (optional)

When `preferred_voice_mode` is `gemini_tts_elevenlabs`, swap the voice while keeping the Gemini performance:

```
POST https://api.elevenlabs.io/v1/speech-to-speech/{voice_id}?output_format=mp3_44100_128
Header: xi-api-key: {ELEVENLABS_API_KEY}
Content-Type: multipart/form-data

Body:
- audio: WAV (from Gemini TTS)
- model_id: eleven_multilingual_sts_v2
- voice_settings: JSON {stability, similarity_boost, style, use_speaker_boost}
```

- `voice_id` and `voice_settings` come from `identity.json.voice_generation_canon.elevenlabs_sts`.
- Back up the original (`*_raw`) and always use the raw as the STS source (idempotent — re-run without degrading).
- Save the config used to `voice_change.json`. The canonical final audio is `audio_final.mp3` / `audio_final.wav`.
- **Requires** `ELEVENLABS_API_KEY` in env. Never print the key.

## Common errors

1. **`systemInstruction` → 400** — all context goes in `text`.
2. **Audio tags only work in English** — `[excited]`, not a translated tag.
3. **Retry on 500** — Gemini TTS sometimes returns text instead of audio. Retry.
4. **Quality degrades past ~2 min** — keep each clip under ~15 seconds.
