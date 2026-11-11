# Avatar Spec — avatar visual consistency (risk #1)

Avatar consistency across shots is the number-one risk of any avatar pipeline. In `avatar_reel`, appearance is fixed by the **trained HeyGen avatar** (`heygen_avatar_id`), but everything else that breaks consistency (background, framing, look, gestures, lipsync) is decided per run. The **Avatar Spec** is the canonical contract that pins those, validated on **every** render.

## Source of truth

- Per identity: `identity.json → identities.<owner>.visual_spec`.
- Emitted automatically into the run inside `identity_guard.json` (field `visual_spec`) when you run `scripts/identity_guard.py`.

## What the spec pins

| Field | Purpose |
|---|---|
| `appearance_source_of_truth` | Face/hair/features are fixed by the `heygen_avatar_id`. **Never** invent facial features in prompts. |
| `visual_reference_dir` | Optional pool of real photos for likeness QA (not for generation). |
| `wardrobe` | The trained avatar's wardrobe; not changed per scene. A different outfit = a different declared look. |
| `background` | The avatar render background (flat neutral). The b-roll on top brings the color. |
| `render_aspect_ratio` / `render_resolution` | HeyGen render params (e.g. 16:9 720p) composed into the 9:16 master. |
| `framing_default` / `approved_framings` | Waist/torso framing with visible hands; a closed list of approved framings. |
| `composite_placement` | Where the avatar sits in the master (bottom 40%, `split_line_y=1152`). |
| `approved_expressions` | Expressions allowed in `avatar_motion_plan.json`. |
| `negative_rules` | What invalidates a shot (hand warping, double face, identity change, wrong background, lipsync drift). |
| `acceptance_checklist` | Render acceptance gate — see below. |

## How it is injected (mandatory)

1. **Before `avatar`**: run `identity_guard.py`; confirm `identity_guard.json.visual_spec` exists.
2. **In the request**: `video_request.json` must reflect the spec — `background`, `aspect_ratio`, `resolution`, `framing`, `hands_visible_requested` come from the spec, not ad-hoc.
3. **In `avatar_motion_plan.json`**: `expression` ∈ `approved_expressions`, `framing` ∈ `approved_framings`.

## Render acceptance gate (mandatory, stage `avatar`)

After downloading `video_avatar.mp4`, validate against `visual_spec.acceptance_checklist` and write `avatar_render_qa.json`:

```json
{
  "stage": "avatar",
  "avatar_id": "<heygen_avatar_id>",
  "engine_confirmed": "avatar_v",
  "checks": {
    "face_full_no_warping": true,
    "hands_visible_well_formed": true,
    "background_correct": true,
    "lipsync_matches_audio_final": true,
    "same_look_as_other_shots": true
  },
  "frames_reviewed": ["qa/avatar_hook.png", "qa/avatar_mid.png", "qa/avatar_end.png"],
  "status": "pass"
}
```

- Extract at least 3 frames (start/mid/end) and review them critically.
- If **any** check fails → `status: "revise"`, do **not** proceed to `composite`, re-render in HeyGen v3 (same identity). Do not "fix" a render with warped hands in post.
- For a reel with several avatar shots: every shot must pass the same gate and share the look. A shot with a different crop/look gets re-rendered.

## Why it matters for realism

Without this spec, nothing catches a HeyGen render with deformed hands, the wrong crop or drifted lipsync before it enters the final composite. The gate turns "it came out weird" into a reproducible checkpoint — which is exactly where avatar realism is won or lost.
