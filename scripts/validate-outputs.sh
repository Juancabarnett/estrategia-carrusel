#!/usr/bin/env bash
# validate-outputs.sh — detects files/folders outside the structure defined in CONTRACT.md
# Usage: bash scripts/validate-outputs.sh   (exit 0 = clean, exit 1 = violations)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

ALLOWED_FLOWS="avatar"          # extend if you add more flows
ALLOWED_OUTPUTS_EXTRA="_audits"
viol=0

note() { printf '  x %s\n' "$1"; viol=$((viol+1)); }

echo "== Validating structure against CONTRACT.md =="

# 1) outputs/ top-level: only allowed flows + extras
if [ -d outputs ]; then
  for entry in outputs/*/; do
    [ -e "$entry" ] || continue
    name="$(basename "$entry")"
    case " $ALLOWED_FLOWS $ALLOWED_OUTPUTS_EXTRA " in
      *" $name "*) : ;;
      *) note "outputs/$name/  -> non-canonical folder in outputs/ (move to scratch/ if a probe, or outputs/<flow>/<run_slug>/)" ;;
    esac
  done
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    note "$f  -> loose file in outputs/ (must live inside outputs/<flow>/<run_slug>/)"
  done < <(find outputs -maxdepth 1 -type f ! -name '.*' 2>/dev/null)
fi

# 2) legacy/wrong folders at the root that indicate a misplaced run
for bad in output runs; do
  if [ -d "$bad" ]; then
    note "$bad/  -> forbidden folder at the root (production runs go to outputs/<flow>/<run_slug>/)"
  fi
done

echo "== Result =="
if [ "$viol" -eq 0 ]; then
  echo "  OK — no violations."
  exit 0
else
  echo "  $viol violation(s). Fix per CONTRACT.md before closing the run."
  exit 1
fi
