# OUTPUT CONTRACT

> **Single source of truth** for where files are written. If a `SKILL.md`, a `contract.json` or memory says otherwise, **this file wins.**

This pack ships with the `avatar` flow. If you add more flows later, extend the table and the validator.

## The 3 critical rules (non-negotiable)

1. **Every deliverable of a run lives in `outputs/<flow>/<run_slug>/`.** Never the repo root, never `brands/`.
2. **`run_slug` = `<kebab-description>-<YYYYMMDD-HHMMSS>`.** Lowercase, dashes, timestamp at the end. One run = one folder.
3. **Probes, experiments, comparisons and temporaries do NOT go in `outputs/`.** They go in `scratch/` (experiments) or `<run>/tmp/` (deletable per-run intermediates).

## Structure

```
outputs/
└── avatar/<run_slug>/     # flow avatar_reel
```

### Inside a run

```
outputs/avatar/my-reel-20260101-143000/
├── run.json                 # canonical run state (required)
├── logs/events.ndjson       # append-only event stream (required)
├── final.mp4                # final deliverable, canonical name
├── source_assets/           # inputs (downloads, refs)
└── tmp/                      # regenerable intermediates — deletable without notice
```

## Intermediates and temporaries

- **Per-run intermediates** (previews, crops, discarded frames): `outputs/avatar/<run_slug>/tmp/`. Deletable any time.
- **Experiments / probes / comparison batches / one-off scripts**: `scratch/`. Never in `outputs/`.
- **Downloaded references / external analysis**: `_research/`.
- **Reusable automation**: `scripts/`.
- **Shared SFX (all flows)**: `sfx/<category>/<slug>.mp3` + an entry in `sfx/library.json`. The only SFX library; a run copies what it uses into `<run>/sfx/`.

## Before closing a run

```bash
bash scripts/validate-outputs.sh
```

If it reports files out of structure, move them to the right place **before** closing the run.
