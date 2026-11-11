---
name: script-framework
description: "Editorial lens for short-form spoken scripts: hooks, retention, rehooks, viewer tension, speed-to-value, and spoken short-form rhythm. Use as the default thinking layer when writing or reviewing an avatar_reel script, before locking the copy."
---

# SCRIPT-FRAMEWORK — short-form hook & retention lens

A lightweight editorial method for short-form spoken video. It doesn't add a pipeline stage — it changes *how* you write the brief, the hooks and the script so the reel earns the first 3 seconds and holds attention. Use it by default in `avatar_reel`, even if the user doesn't mention it. `/guion-ugc` handles structure and format; this skill handles tension and clarity.

These are general short-form principles. They are not anyone's proprietary method — adapt them to your voice.

## Define before writing

- **viewer** — who is this for, specifically.
- **pain_or_desire** — the itch the reel scratches.
- **core_promise** — what the viewer gets if they stay.
- **central_tension** — the contradiction, surprise or stakes that pull them through.
- **selected_angle** — the one lens you tell it through.
- **emotional_target** — pick one: relief, surprise, urgency, confidence, humor, awe, tension.

## Hook principles (first 3 seconds)

- **One idea, one question, one promise.** A hook that asks three blurry questions asks none. Implant a single curiosity gap.
- **Comprehensible without context.** The first beat must land with zero external setup.
- **Speed to value.** No greetings, no throat-clearing, no context that doesn't raise clarity or curiosity. Enter mid-motion.
- **Contrast is the engine.** "but", "actually", "the problem isn't A, it's B" — contrast drives the hook and every rehook.
- **Visual + auditory.** What's in frame 1 and the first spoken line must both pull. One alone isn't enough.
- Always produce **2-3 real hook variants** with different angles so the user can choose.

## Retention & rehooks

- **One strong idea per beat.** If a line needs two visuals or two explanations, split it.
- **Every beat must add** clarity, curiosity or visual evidence. If it doesn't, cut it.
- **Rehooks are real, not decorative.** Plant at least one genuine "the next thing is more valuable" turn before the midpoint when length allows. A transition that just changes the subject is not a rehook.
- **The visual is silent proof.** Let the b-roll demonstrate while the voice frames, translates and lands. Don't narrate over everything that's already visible.

## Spoken short-form rhythm

- Write **speakable, syncable units**: short, breathable lines (~1.5-4.0s spoken). If a line runs long in TTS, split it.
- Alternate very short lines with the occasional medium one. Perfect symmetry sounds scripted.
- Each line should be convertible to audio and a caption chunk without inventing timing.

## Review checklist (gate before TTS)

Put these in `editorial_review.json` and don't pass with a failing one (unless the user explicitly asks):

- `framework_applied` — viewer, promise, tension, hook, rehook and payoff are all clear.
- `first_3s_clarity` — the first beat is understandable with no external context.
- `one_question_hook` — the hook implants one main question, not three blurry ones.
- `speed_to_value` — it reaches the value without delay.
- `rehooks_present` — at least one real rehook before the midpoint when duration allows.
- `spoken_shortform_rhythm` — lines are recordable, short and caption-compatible.

If the input is a long source, a demo or complex material, don't write the most complete summary: find the single strongest idea and turn it into a short-form piece with tension, visual proof and a payoff.
