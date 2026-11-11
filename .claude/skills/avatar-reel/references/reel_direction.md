# Reel Direction — the avatar_reel Creative Direction Document

A **single visual contract** that consolidates the scattered aesthetic decisions (b-roll design system, avatar background/framing, title palette, caption treatment) into one artifact that is **injected downstream** into `hook_visual`, `broll`, `composite`, `captions` and `final`.

It solves the problem of having several visual "defaults" stepping on each other. Each run makes **one** explicit, traceable decision instead of re-deciding ad-hoc every time.

## Where it sits in the flow

- Stage: part of the editorial layer, **after** `visual_beat_plan.json` and **before** `hook_visual`/`broll`.
- Artifact: `reel_direction.json` at the run root (optionally a readable `reel_direction.md`).
- Written by `avatar-reel`; consumed by `hook_visual`, `broll`, `composite`, `captions`, `final`.

## B-roll visual system decision tree (single arbitration rule)

**Your brand defines its own systems.** Pick **one** `broll_design_system` with this priority — this is the rule that settles which default wins:

1. **`brand_system`** — your approved brand visual system for the topic (palette, type, components). Wins over everything.
2. **`topic_system`** — a system you maintain that is tied to the subject matter (e.g. a particular product/partner). Use it only if you have one.
3. **`default_system`** — your house default for everything else.

> The original pipeline this pack is derived from kept named systems like a "dark glass UI" look and a "paper editorial" look. Don't inherit those — define the 1-3 visual systems that are actually yours, give them names, and document them in your project. The arbitration rule is what matters, not the specific systems.

**Downloaded factual material** (screenshots, posts, demos, source videos) is **orthogonal** to the design system: it shows as a clean proof card *inside* the chosen system, or `contain`/full-frame when the asset itself must be read. It is not a fourth competing "default" — it is content that lives **inside** the chosen system. Record per-asset `framing_strategy` (`contain_full_frame` / `cover_guided_pan` / `mixed`) in `broll_timing.json`.

## `reel_direction.json` schema

```json
{
  "version": 1,
  "stage": "reel_direction",
  "broll_design_system": "default_system",
  "design_system_source": "default | brand | topic | user",
  "design_system_rationale": "Why this system fits the topic and the audience.",
  "avatar_treatment": {
    "background": "#0A0A0A",
    "framing": "waist_up_hands_visible",
    "from_avatar_spec": true,
    "note": "These come from the Avatar Spec (identity.json.visual_spec). Do not reinvent per run."
  },
  "title_treatment": {
    "enabled": true,
    "palette": "brand",
    "card_bg": "#111111",
    "line1_color": "#FFFFFF",
    "line2_color": "#FFFFFF",
    "max_lines": 2,
    "max_words": 6,
    "note": "Neutral defaults. Set card_bg / line colors to your brand in avatar_reel_post_canon.json."
  },
  "caption_treatment": {
    "component": "white_editorial_chunks",
    "placement": "above_avatar_split_on_broll",
    "color": "#FFFFFF",
    "accent_color": null,
    "max_words_per_caption": 3
  },
  "motion_grammar": {
    "hook_cuts_s": [0.7, 1.5],
    "beat_length_s": [4, 7],
    "layout_variety_min": 4,
    "no_static_over_s": 10
  },
  "negative_visual_rules": [
    "do not mix two design systems in the same reel without an editorial reason",
    "no captions with an accent color unless an approved brand system says so",
    "no overlays on factual material the user needs to see clean"
  ]
}
```

## How it is injected downstream

- `hook_visual` and `broll`: `broll_design_system` and `motion_grammar` drive the look of the b-roll and the edited hook.
- `composite`: `avatar_treatment` (from the Avatar Spec) fixes background/framing.
- `captions`: `caption_treatment` fixes component/color/placement (default white, no accent).
- `final`: `title_treatment` and the palette close end cards and the title plate.

## Relationship to the other sidecars

- **Avatar Spec** (`identity.json.visual_spec`) = who the avatar is and how it looks/frames. Invariant per identity.
- **Reel Direction** (`reel_direction.json`) = how **this** reel looks (design system, title, captions, motion). Per run.
- **visual_beat_plan.json** = what happens in each beat. Reel Direction gives it the visual language; the beat plan gives it the content.

Don't duplicate: `avatar_treatment` references the Avatar Spec with `from_avatar_spec: true` instead of re-copying values that could diverge.
