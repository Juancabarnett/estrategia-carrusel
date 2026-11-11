---
name: avatar-reel
description: "Orchestrate the complete avatar_reel flow from a single trigger to a finished vertical reel: source harvest, script, voice, avatar render, hook visual, b-roll, captions, music, SFX and final mix. The avatar speaks in the user's own voice and likeness. Use when the user wants a 9:16 talking-head reel built automatically from a topic, link, or asset."
---

# AVATAR-REEL — flow orchestrator

You coordinate the full `avatar_reel` flow: from a trigger (a topic, a link, an asset) to a finished vertical reel where **the user's own avatar speaks in their own voice**, over designed b-roll, with captions, music, SFX and an automatic final mix.

The contractual source of truth is `contract.json` in this folder. The post-production canon (title, captions, mixing, QA) lives in the **`avatar-reel-editing`** skill. The speaker identity lives in **`identity.json`** in this folder — that is the only file the user must adapt to make the pack theirs.

> **This pack is brand-agnostic.** It does not ship anyone's voice, look, visual style or editorial method. You bring your own avatar, voice and design language. Where this skill says "your brand decides", it means exactly that.

## Output contract

Every deliverable of a run goes to **`outputs/avatar/<run_slug>/`** — never the repo root, never `brands/`. `run_slug = <kebab-description>-<YYYYMMDD-HHMMSS>`. Probes/experiments go to `scratch/`; per-run intermediates go to `<run>/tmp/`. See **[CONTRACT.md](../../../CONTRACT.md)** and run `bash scripts/validate-outputs.sh` before closing a run.

## Stages

| Stage | Owner | Canonical outputs |
|---|---|---|
| `source_harvest` | this skill | `source_assets/*`, `source_assets/manifest.json`, `creative_brief.json`, `hook_variants.json`, `angle_selection.json`, `visual_beat_plan.json`, `reel_direction.json` |
| `script` | `/guion-ugc` + `/script-framework` | `script.txt`, `script.md`, `script.json`, `editorial_review.json` |
| `tts` | `/tts-ugc` (ElevenLabs Eleven v4) | `audio_final.mp3`, `audio_final.wav` |
| `voice_change` (not used, always `skipped`) | `/tts-ugc` | none |
| `avatar` | this skill (HeyGen Avatar V) | `video_avatar.mp4`, `avatar_motion_plan.json`, `video_request.json`, `video_result.json`, `asset_upload.json`, `avatar_render_qa.json` |
| `hook_visual` | this skill + `/avatar-reel-editing` | `hook_visual_plan.json`, `title_card_reference_v2.png`, `title_card_manifest.json`, `hook_visual.mp4` |
| `broll` | this skill + `/avatar-reel-editing` (HyperFrames / downloaded factual material) | `broll_top.mp4`, `broll_timing.json`, `broll_hyperframes*/` |
| `composite` | `/avatar-reel-editing` | `video_composite.mp4` |
| `captions` | `/avatar-reel-editing` | `captions.srt`, `captions.words.json`, `captions_style.json`, `hyperframes_captions_project/`, `composite_captioned.mp4` |
| `music` (optional) | `/music-ugc` + `/avatar-reel-editing` | `music.mp3`, `music_prompt.json`, `music_task.json`, `final_mix_manifest.json` |
| `sfx` (optional) | `/sfx-ugc` + `/avatar-reel-editing` | `sfx_plan.json`, `sfx/` |
| `final` | `/avatar-reel-editing` | `final.mp4`, `post_render_qa_report.json` |

When an optional stage doesn't apply, mark it `skipped` and continue.

## External dependencies (install once)

The **HyperFrames** skills (`hyperframes`, `hyperframes-cli`, `hyperframes-media`, `hyperframes-registry`) are bundled in this pack — use them for b-roll, title cards and Smart Captions authoring. The other tools below are runtimes/services the flow drives but does not bundle; install them before running (see `SETUP.md`):

- **HyperFrames runtime** — the engine itself runs via `npx hyperframes@latest` (init / add / render / transcribe), so Node must be installed even though the skills are bundled.
- **`$video-perception`** — video analysis (the `claude-video-vision` Claude Code plugin / MCP). Used in `source_harvest` and QA. Optional but recommended when the source is video.
- **HeyGen** — the avatar render. Either the `heygen` CLI or a direct `POST /v3/videos` call. Needs `HEYGEN_API_KEY` + `AVATAR_GROUP_ID`.
- **FFmpeg**, **Python 3 + Pillow** — local audio/video processing for the editing scripts.

---

## Identity gate (mandatory before tts / voice_change / avatar)

Resolve the speaker and write `identity_guard.json` into the run **before** generating final audio or calling HeyGen.

- Canonical source: **`identity.json`** in this folder. The user fills it once.
- Default owner is whatever `default_owner` points to (the pack ships `me`).
- Run the guard to emit the sidecar:

```bash
python3 .claude/skills/avatar-reel/scripts/identity_guard.py \
  --run-dir "$RUN_FOLDER" \
  --owner me
```

- The sidecar carries `heygen_avatar_id`, `elevenlabs_voice_id`, `visual_spec` and `voice_generation_canon` into the run.
- If the resolved `avatar_id` / `voice_id` contradicts what the user asked for, **stop** and mark `avatar`/`voice_change` as `failed` with `error.code: "identity_mismatch"`. Never silently infer a different identity.
- If you keep more than one identity, list any that must never be used as a fallback under `blocked_unless_explicit_owner` — the guard enforces it.

## Avatar Spec — visual consistency (risk #1)

Avatar consistency across shots is the number-one risk of any avatar pipeline. The face/hair/features are fixed by the trained HeyGen avatar; everything else that breaks consistency (background, framing, gestures, lipsync) is pinned by the **Avatar Spec** and validated on **every** render. Full reference: **[`references/avatar_spec.md`](references/avatar_spec.md)**.

- Source: `identity.json → identities.<owner>.visual_spec`, emitted to the run inside `identity_guard.json.visual_spec`.
- **Do not invent facial features in prompts.** The avatar id is the source of truth for appearance.
- `video_request.json` takes `background`, `aspect_ratio`, `resolution`, `framing`, `hands_visible_requested` from the spec, not ad-hoc.
- **Render acceptance gate (mandatory):** after downloading `video_avatar.mp4`, extract ≥3 frames (start/mid/end), validate against `visual_spec.acceptance_checklist`, and write `avatar_render_qa.json` with `status: "pass" | "revise"`. If any check fails (hand warping, double face, wrong crop, wrong background, lipsync drift, look mismatch), do **not** proceed to `composite`: re-render in HeyGen v3 with the same identity. A render with deformed hands is not fixed in post.

## HeyGen Avatar V (the avatar render)

Every avatar render must use **Avatar V** explicitly and verifiably.

- Use `POST /v3/videos`. You may use `heygen video create` only if that CLI accepts the `engine` field (`heygen video create --request-schema | grep engine`); otherwise call `/v3/videos` directly so `engine.type` is not lost.
- The request body **must** include `"engine": { "type": "avatar_v" }`. If `engine` is omitted, HeyGen v3 falls back to Avatar IV by default — do not render; fail the stage with `error.code: "avatar_v_request_missing"`.
- Do not send `avatar_style`. With the current public schema, also do not send `motion_prompt` or `expressiveness` (those are Avatar IV only); only add Custom Motion fields if the live schema explicitly exposes them for Avatar V.
- Before a paid render, verify the chosen look supports Avatar V: `GET /v3/avatars/looks/{look_id}` (or `heygen avatar looks get <id>`) must return the look with `"avatar_v"` in `supported_api_engines` and a ready status. If not, fail with `error.code: "avatar_v_unavailable"`. No silent fallback to Avatar IV/III or legacy endpoints.
- Do not use external lipsync providers (Sync, fal sync-lipsync, Kling lip sync, `heygen lipsync`) as a fallback for this flow. If HeyGen fails (credits, queue, API, render error), the `avatar` stage stays `failed` and waits for a HeyGen retry.

### Credentials & environment

- The HeyGen CLI uses `HEYGEN_API_KEY`. The flow needs at least `HEYGEN_API_KEY` and `AVATAR_GROUP_ID` (used to list your private looks). `AVATAR_LOOK_ID` is optional and should match `identity.json`.
- Hydrate env from `$PROJECT/.env` and/or the harness env before calling HeyGen. **Never** print secret values into logs, sidecars or responses.
- If `HEYGEN_API_KEY` or `AVATAR_GROUP_ID` are missing, fail `avatar` with `error.code: "missing_heygen_env"` and do not try another provider.

### Canonical Avatar V command

1. Resolve identity → `identity_guard.json` (see above).
2. Validate the look supports Avatar V:

```bash
LOOK_ID="$(jq -r .heygen_avatar_id "$RUN_FOLDER/identity_guard.json")"
curl -s --request GET \
  --url "https://api.heygen.com/v3/avatars/looks/$LOOK_ID" \
  --header "x-api-key: $HEYGEN_API_KEY" \
  > "$RUN_FOLDER/avatar_look_raw.json"
# require: id == LOOK_ID, status completed, supported_api_engines includes "avatar_v"
```

3. Upload the final audio:

```bash
heygen asset create --file "$RUN_FOLDER/audio_final.mp3" > "$RUN_FOLDER/asset_upload.raw.json"
# extract data.asset_id -> asset_upload.json.audio_asset_id
```

4. Build `avatar_motion_plan.json` (intent) and the real request body. Base request:

```json
{
  "type": "avatar",
  "avatar_id": "<heygen_avatar_id from identity_guard.json>",
  "audio_asset_id": "<asset_id>",
  "engine": { "type": "avatar_v" },
  "background": { "type": "color", "value": "#0A0A0A" },
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "output_format": "mp4",
  "title": "<clear render title>"
}
```

Default editorial framing is medium shot with hands in frame: `expression: "confident"|"sincere"`, `gaze: "looking_at_camera"`, `framing: "waist_up_hands_visible"`, `hands_visible_requested: true`. If the live schema does not expose Avatar V Custom Motion, render plain Avatar V and record `api_support_status: "not_exposed"` in `avatar_motion_plan.json` — don't block the stage over it.

5. Render and poll:

```bash
curl -s --request POST \
  --url "https://api.heygen.com/v3/videos" \
  --header "Content-Type: application/json" \
  --header "x-api-key: $HEYGEN_API_KEY" \
  --data @"$RUN_FOLDER/video_request.body.json" \
  > "$RUN_FOLDER/video_create.raw.json"
# extract data.video_id, poll GET /v3/videos/{video_id} until completed/failed, download as video_avatar.mp4
```

For a split layout, render the avatar at `16:9` and compose it into the bottom of the 9:16 master. `video_result.json` must keep `provider: "heygen"`, `api_path: "/v3/videos"`, `engine: {"type":"avatar_v"}` and the `video_id`.

---

## Editorial layer (before locking the script)

Avatar reels live or die on the first 3 seconds. Before writing the final script, run a light editorial method. It doesn't add a stage — it lives as sidecars.

### Script framework

Write the script with **`/script-framework`** as the default editorial lens (hooks, retention, rehooks, viewer tension, spoken short-form rhythm), even if the user doesn't mention it. The goal is to write `creative_brief.json`, `hook_variants.json`, `angle_selection.json`, `visual_beat_plan.json` and the script better — not to add bureaucracy. `/guion-ugc` handles structure and format.

In `creative_brief.json`, always include:

```json
{
  "framework": {
    "viewer": "",
    "pain_or_desire": "",
    "core_promise": "",
    "central_tension": "",
    "selected_angle": "",
    "emotional_target": "",
    "script_mode": "short_form_avatar_reel"
  }
}
```

### Evidence first

For news, research, launches or social-listening topics, `source_harvest` must collect real visual evidence before the script: public posts, videos, official blogs, changelogs, screenshots, benchmarks. If the user sends video assets (or YouTube/social links that resolve to video), analyze them with `$video-perception` first and write `source_assets/video_perception_manifest.json`. The editorial sidecars must cite that evidence by `asset_id` + timestamp.

### Mini editorial autoplan

Write `creative_brief.json` before the final script. It answers: `promise`, `viewer_importance`, `tension`, `takeaway`, `proof_visual`, `weak_reel` (what a weak version of this same topic looks like), `audience`, `source_evidence`.

Then generate real options before choosing:

- `hook_variants.json`: ≥3 hooks, each with `text`, `first_3s_visual`, `promise`, `risk`.
- `angle_selection.json`: 2-3 candidate angles with `why_it_matters`, `visual_proof`, `tradeoffs`, and a justified `selected_angle_id`.
- `visual_beat_plan.json`: 2 alternative beat structures; pick one with `selected_structure_id`.

### Hook gate

Always deliver the script **with 3 real hook alternatives** for the user to choose. Unless the user explicitly said "do the whole pipeline / render / generate everything", **stop after `script`**, leave the run waiting for a hook decision, and ask before `tts`. When the user picks a hook, update `hook_variants.json.selected_hook_id` and continue only when authorized.

### Review gate before TTS

Before starting `tts`, write `editorial_review.json` with `status: "pass" | "revise"`. Checklist: `framework_applied`, `first_3s_clarity`, `one_question_hook`, `speed_to_value`, `rehooks_present`, `one_idea_per_beat`, `broll_proves_or_amplifies`, `first_frame_clear`, `factual_evidence_used`, `weak_reel_avoided`. Do not pass to `tts`/`avatar`/expensive render with `status: "revise"` unless the user asks.

---

## Reel Direction (one visual contract)

Before `hook_visual`/`broll`, consolidate the aesthetic decisions into a single `reel_direction.json`. Full schema: **[`references/reel_direction.md`](references/reel_direction.md)**.

Its main job is to settle **which b-roll visual system** the reel uses, with a single arbitration rule (so you don't have three competing "defaults"). **Your brand defines its own systems.** Pick one `broll_design_system` by priority:

1. `brand_system` — your approved brand visual system (palette, type, components). Wins over everything.
2. `topic_system` — a system tied to the subject matter, if you maintain one.
3. `default_system` — your house default for everything else.

Downloaded factual material (screenshots, posts, demos) is **orthogonal** to the design system: it shows up as a clean proof card *inside* the chosen system, or `contain`/full-frame when the asset itself must be read. Record `framing_strategy` per asset in `broll_timing.json`.

`reel_direction.json` also pins `avatar_treatment` (referencing the Avatar Spec with `from_avatar_spec: true`), `title_treatment`, `caption_treatment` and `motion_grammar`, injected downstream into `hook_visual`, `broll`, `composite`, `captions`, `final`.

---

## Post-production canon (title, b-roll, captions, mix)

The hard values for the split layout, title card, captions and final mix live in **`avatar-reel-editing`** and its `references/avatar_reel_post_canon.json`. Read those before `hook_visual`, `composite`, `captions` or `final`. Highlights (all overridable in the canon JSON):

- **Layout:** `1080x1920`, b-roll on top (`1080x1152`, 60%), avatar at the bottom (`1080x768`, 40%), `split_line_y=1152`.
- **Captions:** uppercase, white, black outline, single line, ≤3 words/chunk, no background box. Above the avatar seam, on the b-roll, never on the avatar's face/hands. Above the title while it's visible (`y=1000`), below it after (`y=1120`). Timing from word timestamps reconciled to the final script — never raw ASR as the final copy. Build them with `avatar-reel-editing/scripts/build_avatar_reel_captions.py`.
- **Title card:** ≤2 lines, ≤6 words, crosses the split line, animated in/out. Colors/font are neutral in the canon — set them to your brand. Render with `avatar-reel-editing/scripts/render_title_card.py`.
- **Mix:** voice is primary; music is a subtle bed with real sidechain ducking (`music_volume≈0.08`, not 0.3). Mix with `avatar-reel-editing/scripts/mix_avatar_reel_audio.py`.

### B-roll discipline (generic)

- Edit b-roll as a timeline with an EDL, not as filler. Do not repeat a clip, `media_start`, scene or visual range before exhausting the useful ranges. Record per beat `asset`, `media_start`, `source_end`, `framing_strategy` and the editorial reason in `broll_timing.json`.
- Per-asset framing is a decision: `contain`/full-frame when the audience must read the whole asset (black bars are fine if intentional), `cover` with guided zoom/pan when you want to direct the eye, `mixed` when you start wide then push in. Never blind crop-fill that cuts UI, text, product or action.
- If the script says a URL, command, snippet or exact step, it must appear on screen as a short legible plate during the spoken line — not only in voice/captions.
- No more than ~10s without a substantive visual change. Vary layouts; don't repeat two consecutive beats with the same composition.
- QA every render with `$video-perception` (or equivalent frame sampling): no black frames, no broken crops, no caption collisions, no long freezes, no visual loop while useful material is unused. Save findings to `broll_visual_qc.json` / `post_render_qa_report.json`.

### SFX (optional sound design)

Strategic sound effects anchored to **visual events** (title in/out, b-roll cuts on rehooks, proof card entry, reveal, CTA) — never to words or captions. Sourcing/plan via **`/sfx-ugc`** (library-first: `sfx/library.json`); the mix runs in `final` via `/avatar-reel-editing`. Budget: 4-8 hits per 30s, max 1 per beat (hook allows 2), ≥2s apart. The voice always wins: no hit masks the start of a phrase. Mark `skipped` if the user wants a reel without SFX.

---

## Operating rules

1. Work inside `$RUN_FOLDER`. Don't invent outputs that aren't on disk.
2. Per stage: set `status: "running"` + `started_at` at start; `status: "done"` + `ended_at` + `artifacts[]` at end; on failure `status: "failed"` + `error.code/message/suggestions`.
3. Append `stage.started/progress/done/failed` to `logs/events.ndjson`.
4. Close the flow with `final_artifact: "final.mp4"` when the real master exists.
5. `identity_guard.json` is mandatory before `audio_final.*` or any HeyGen call.
6. Audio hygiene: `audio_final` fixes the reel duration (HeyGen renders over it). The chain `audio_final.duration → video_avatar → composite → captions end → music length` must close on the same number. Don't leave >~120ms of dead air at start/end.
7. Captions: source text is the **corrected final script**, not raw ASR. Use `--language <your-lang>` for transcription; never Whisper `.en` models on non-English audio.
8. Mix: if there's music, ducking is mandatory and a key phrase must never be masked. If a run ships without music, mark it explicitly (`music.skipped`) in `final_mix_manifest.json`.

## Orchestration notes

- Use `/guion-ugc`, `/script-framework`, `/tts-ugc`, `/music-ugc`, `/sfx-ugc` for the stages that have their own skill. Designed b-roll (HyperFrames) and downloaded factual b-roll are built by this skill + `/avatar-reel-editing`.
- Use `/avatar-reel-editing` for the runtime post: title, split composite, captions, music/voice mix and delivery QA. If `avatar-reel-editing/references/avatar_reel_post_canon.json` conflicts with this file, the canon JSON wins.
- This skill owns direction/orchestration and the editorial sidecars; it must not duplicate or improvise the post canon.
