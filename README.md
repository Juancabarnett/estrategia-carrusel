# Avatar Reel Pack

Generate a vertical (9:16) short-form **reel where your own avatar speaks in your own voice** — from a single trigger (a topic, a link, an asset) to a finished video with b-roll, captions, music, SFX and an automatic final mix.

This is a set of [Claude Code](https://claude.com/claude-code) **skills**. You drop them into a project, tell the agent what the reel is about, and it runs the whole pipeline: script → voice → avatar render → hook visual → b-roll → captions → music/SFX → final mix.

> **Brand-agnostic by design.** This pack ships **no one's** voice, face, visual style or editorial method. You bring your own HeyGen avatar, your own voice, and your own design language. Everything that was specific to its original author has been stripped out and replaced with neutral defaults and `<PLACEHOLDERS>`.

---

## What's in the box

```
avatar-reel-pack/
├── README.md                  ← you are here
├── SETUP.md                   ← install the external tools (HeyGen, HyperFrames, ffmpeg…)
├── env.example                ← rename to .env and fill in your API keys (names only, no secrets)
├── CONTRACT.md                ← where runs write their files
├── scripts/validate-outputs.sh
├── sfx/                        ← shared SFX library (index + recipe; mp3s not shipped)
└── skills/                    ← ALL 11 skills (copy this into <your-project>/.claude/skills/)
    ├── avatar-reel/           ← THE ORCHESTRATOR (+ identity.json ← edit this)
    ├── avatar-reel-editing/   ← post: title, captions, mix, QA (+ python scripts)
    ├── guion-ugc/             ← script generator
    ├── script-framework/      ← hook / retention editorial lens
    ├── tts-ugc/               ← voice (Gemini TTS → optional ElevenLabs clone)
    ├── music-ugc/             ← instrumental music (Suno via Kie.ai)
    ├── sfx-ugc/               ← sound design (+ sfx_lib.py)
    ├── hyperframes/           ← HTML→video engine: how to author b-roll/title/captions
    ├── hyperframes-cli/       ← the hyperframes dev-loop CLI (init/lint/render)
    ├── hyperframes-media/     ← asset prep (tts/transcribe/remove-bg)
    └── hyperframes-registry/  ← installing registry components (captions, blocks)
```

> **Why a `skills/` folder?** Claude Code discovers skills in a **hidden** `.claude/skills/` folder inside your project. This pack ships them in a plain, **visible** `skills/` folder so you can see everything — the install step below just moves them into place. (Claude Code only auto-loads them once they're under `.claude/skills/`.)

> The four `hyperframes-*` skills teach the agent how to drive HyperFrames. They are bundled so the pack is self-contained — but the actual engine still runs via `npx hyperframes@latest` at render time, so you still need Node installed (see SETUP).

## The pipeline

| Stage | Does | Tool |
|---|---|---|
| `source_harvest` | research, hooks, angle, visual beat plan, reel direction | the orchestrator (+ `$video-perception` for video sources) |
| `script` | spoken script + 3 hook variants + editorial review | `guion-ugc` + `script-framework` |
| `tts` | the voice, in your performance direction | `tts-ugc` (Gemini TTS) |
| `voice_change` *(optional)* | swap in your cloned voice | `tts-ugc` (ElevenLabs STS) |
| `avatar` | the talking-head render | HeyGen Avatar V (`/v3/videos`) |
| `hook_visual` | animated title card + hook edit | `avatar-reel-editing` (HyperFrames) |
| `broll` | designed/factual b-roll, edited as a timeline | `avatar-reel-editing` (HyperFrames) |
| `composite` | 9:16 split: b-roll on top (60%), avatar bottom (40%) | `avatar-reel-editing` |
| `captions` | word-synced editorial captions | `avatar-reel-editing` (HyperFrames Smart Captions) |
| `music` *(optional)* | instrumental bed | `music-ugc` (Suno) |
| `sfx` *(optional)* | strategic hits on visual events | `sfx-ugc` |
| `final` | voice + music + SFX mix with ducking, QA | `avatar-reel-editing` |

---

## Quick start

1. **Install the runtimes** → see [SETUP.md](SETUP.md). The skills are all here; you still need: Claude Code, ffmpeg, Python 3 + Pillow, Node (HyperFrames runs via `npx` at render time), the HeyGen CLI (or just `curl`), and a `$video-perception` plugin if you feed it video.

2. **Install the skills into your project.** At the root of a Claude Code project (an empty folder works):
   - copy this pack's **`skills/`** contents into **`.claude/skills/`** — e.g. `mkdir -p <project>/.claude/skills && cp -R skills/* <project>/.claude/skills/`
   - copy **`sfx/`**, **`scripts/`** and **`CONTRACT.md`** to the project root.

   (The `.claude` folder is hidden in Finder — press `Cmd+Shift+.` to see it. That's normal; Claude Code requires that exact name.)

3. **Make it yours — edit ONE file:** `skills/avatar-reel/identity.json` (becomes `.claude/skills/avatar-reel/identity.json` after install). This is the only file that defines an identity. Fill in:
   - `heygen_avatar_id` — your trained HeyGen avatar.
   - `voice_generation_canon` — your Gemini voice + performance direction (accent, energy, pacing). Neutral defaults are provided; rewrite them to your speaker.
   - `elevenlabs_voice_id` — only if you want to swap in a cloned voice (`preferred_voice_mode: "gemini_tts_elevenlabs"`).
   - `visual_spec` — background, framing and acceptance checklist for the render.

4. **Add your API keys:** save `env.example` as `.env` at the project root and fill it in. (HeyGen + Gemini are required; ElevenLabs/Suno are optional.)

5. **Optionally brand the look:** colors, fonts and the title card are neutral. Set them in `skills/avatar-reel-editing/references/avatar_reel_post_canon.json` (`title.card.background`, `title.colors`, `title.font.paths`) and define your own b-roll visual systems in `reel_direction` (see `avatar-reel/references/reel_direction.md`).

6. **Run it.** In Claude Code, just describe the reel:
   > "Make me an avatar reel about &lt;topic&gt;. Here's the source: &lt;link or asset&gt;."

   The agent invokes the `avatar-reel` skill, harvests sources, writes the script with **3 hook options**, and stops for you to pick a hook before spending render credits. Approve, and it runs to `final.mp4`.

---

## How to adapt it to YOUR brand

| Want to change… | Edit… |
|---|---|
| Who speaks (avatar + voice) | `avatar-reel/identity.json` |
| Voice accent / energy / pacing / speed-up | `identity.json → voice_generation_canon` |
| Title card color / font / second-line accent | `avatar-reel-editing/references/avatar_reel_post_canon.json → title` |
| Caption color / position / words-per-chunk | `…post_canon.json → captions` |
| Music volume / ducking | `…post_canon.json → audio` |
| B-roll visual system(s) | define your own in `reel_direction` (`avatar-reel/references/reel_direction.md`) |
| Split layout proportions | `…post_canon.json → layout` |

The Python scripts read **every** value from `avatar_reel_post_canon.json`, so editing that JSON re-skins the output without touching code.

---

## Security & privacy

- **No secrets are bundled.** Every skill reads API keys by name from the environment. `.env` is yours and is git-ignored (add it to your `.gitignore`).
- **No biometric identity is bundled.** There is no avatar id, voice id or face in this pack — only `<PLACEHOLDERS>` you fill in. A HeyGen avatar id only works with the matching HeyGen account anyway.
- **The skills never print secret values** into logs, sidecars or responses, by rule.

## License & attribution

The pipeline architecture and the Python helper scripts are yours to adapt. The external services (HeyGen, Gemini, ElevenLabs, Suno/Kie.ai, HyperFrames) have their own terms and pricing — see [SETUP.md](SETUP.md).
