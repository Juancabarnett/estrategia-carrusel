# SETUP — external tools & dependencies

This pack drives a few public tools but does **not** bundle them. Install them once in your project.

## 1. Claude Code

The skills run inside [Claude Code](https://claude.com/claude-code). Copy this pack's visible **`skills/`** folder into a project's **hidden `.claude/skills/`** folder:

```bash
mkdir -p <your-project>/.claude/skills
cp -R skills/* <your-project>/.claude/skills/
cp -R sfx scripts CONTRACT.md <your-project>/
cp env.example <your-project>/.env   # then fill it in
```

The `.claude` folder is hidden in Finder (press `Cmd+Shift+.` to reveal it) — that exact name is required for Claude Code to auto-discover the skills. Once copied, Claude lists them in the skills picker.

## 2. Local toolchain

| Tool | Why | Install |
|---|---|---|
| **FFmpeg** | all audio/video processing in the editing scripts | `brew install ffmpeg` (macOS) · `apt install ffmpeg` (Linux) |
| **Python 3.9+** | the editing & SFX scripts | usually preinstalled; `brew install python` |
| **Pillow** | title-card rendering (`render_title_card.py`) | `pip install pillow` |
| **Node.js 18+** | HyperFrames CLI | `brew install node` or nvm |
| **jq** | JSON in the shell snippets | `brew install jq` |

Quick check:

```bash
ffmpeg -version | head -1
python3 -c "import PIL; print('pillow', PIL.__version__)"
node --version
```

## 3. HyperFrames (b-roll, title cards, captions)

HyperFrames is the HTML→video engine used for designed b-roll, the animated title card and Smart Captions. The **skills** that teach the agent how to author HyperFrames compositions (`hyperframes`, `hyperframes-cli`, `hyperframes-media`, `hyperframes-registry`) are **bundled** in this pack. The **engine** itself is a public npm package the skills call with `npx`, so you only need Node installed — nothing to vendor:

```bash
# scaffold a captions project (the editing skill does this per run)
npx hyperframes@latest init <dir> --example blank --resolution portrait --non-interactive --skip-skills
# install caption components
npx hyperframes@latest add captions --dir <dir> --no-clipboard
# transcribe to word timestamps (set your language)
npx hyperframes@latest transcribe audio_final.mp3 --model small --language <lang> --json
# render
npx hyperframes@latest render <dir> --output out.mp4
```

> Live preview of some HyperFrames blocks needs the Chrome flag `chrome://flags/#canvas-draw-element`. The CLI render handles this automatically.

## 4. HeyGen (the avatar render) — required

You need a HeyGen account with a **trained avatar that supports Avatar V**.

1. Get your API key → put it in `.env` as `HEYGEN_API_KEY`.
2. Find your avatar/look id and group id:
   ```bash
   # CLI (optional): https://github.com/heygen-com — or use the dashboard
   heygen avatar looks list --group-id $AVATAR_GROUP_ID --ownership private --limit 50
   ```
   Put the group id in `.env` as `AVATAR_GROUP_ID`, and the look id in `identity.json` as `heygen_avatar_id`.
3. The flow uses `POST /v3/videos` with `engine.type: "avatar_v"`. The HeyGen CLI is optional — `curl` works (see `avatar-reel/SKILL.md`).

**Avatar V is required.** Verify your look returns `"avatar_v"` in `supported_api_engines` before spending render credits.

## 5. Voice — Gemini (required) + ElevenLabs (optional)

- **Gemini TTS** generates the voice. Get a Google AI Studio key → `.env` as `GEMINI_API_KEY`. Model: `gemini-3.1-flash-tts-preview`.
- **ElevenLabs** is only needed if you want to swap in a *cloned* voice (`preferred_voice_mode: "gemini_tts_elevenlabs"` in `identity.json`). Get a key → `.env` as `ELEVENLABS_API_KEY`, clone your voice in ElevenLabs, and put the `voice_id` in `identity.json`.

If you only use Gemini (`gemini_tts_only`), you don't need ElevenLabs at all.

## 6. Music — Suno via Kie.ai (optional)

For the instrumental bed. Get a [Kie.ai](https://kie.ai) key → `.env` as `KIE_API_KEY` (or `SUNO_KIE_API_KEY`). Skip if you'll add your own music.

## 7. `$video-perception` (optional, recommended for video sources)

When your trigger is a video (a YouTube link, a demo, a social clip), the orchestrator analyzes it before scripting. This uses a video-analysis plugin/MCP for Claude Code (commonly the **`claude-video-vision`** plugin). Install it as a Claude Code plugin if you want video understanding in `source_harvest`. Without it, feed text/links/screenshots instead.

## 8. SFX (optional)

The shipped `sfx/library.json` is an **index** of pointers to the HeyGen sound catalog — the `.mp3` files are not included. To populate real sounds you need the **HeyGen CLI ≥ v0.1.1** (`heygen audio sounds list`). Then:

```bash
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py catalog "soft whoosh" --limit 5
python3 .claude/skills/sfx-ugc/scripts/sfx_lib.py add --slug whoosh-soft --category whoosh --class pitched --url "<audio_url>" --description "..." --use-for "transition"
```

Or build your own library from any source — just keep the `library.json` schema.

## Environment recap

Save `env.example` → `.env` (at your project root) and fill in what you use:

| Key | Required? | For |
|---|---|---|
| `HEYGEN_API_KEY` | ✅ | avatar render |
| `AVATAR_GROUP_ID` | ✅ | listing your looks |
| `GEMINI_API_KEY` | ✅ | voice |
| `ELEVENLABS_API_KEY` | optional | cloned voice |
| `KIE_API_KEY` | optional | music |
| `OPENAI_API_KEY` | optional | Whisper caption fallback |

Add `.env` to your `.gitignore`. Never commit real keys.
