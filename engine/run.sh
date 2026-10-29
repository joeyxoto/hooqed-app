#!/bin/bash
# Flow A short (interactive quote that turns website visitors into booked calls) — one command per business: ./run.sh <url> <outdir>
set -eo pipefail; cd "$(dirname "$0")"; U="$1"; D="${2:-runs/$(echo "$U" | sed -E 's#https?://(www\.)?##; s#[./].*##')}"; mkdir -p "$D"; [ -f "$D/search-hint.json" ] && export HOOQ_HINT="$D/search-hint.json"
echo "recipe $(git rev-parse HEAD 2>/dev/null) $([ -z "$(git status --porcelain pipeline run.sh data)" ] && echo clean || echo DIRTY)" | tee "$D/run.log"
[ -f "$D/scrape.json" ] || python3 pipeline/scrape.py "$U" "$D/scrape.json" | tee -a "$D/run.log"
python3 pipeline/owner_input.py "$D" | tee -a "$D/run.log"
python3 pipeline/locale_detect.py "$D" | tee -a "$D/run.log"
[ -f "$D/facts.json" ] || python3 pipeline/facts.py "$D" | tee -a "$D/run.log"
python3 pipeline/route.py "$D" | tee -a "$D/run.log"   # exit 10 = needs the owner's input (needs-input.json)
[ -f "$D/hooq.raw.json" ] || python3 pipeline/write.py "$D" | tee -a "$D/run.log"
python3 pipeline/validate.py "$D" | tee -a "$D/run.log"
python3 pipeline/images.py "$D" | tee -a "$D/run.log"
python3 pipeline/brand.py "$D" 2>>"$D/errors.log" | tee -a "$D/run.log"
python3 pipeline/build.py "$D" | tee -a "$D/run.log"
python3 pipeline/shots.py "$D" | tee -a "$D/run.log"
python3 pipeline/cost.py "$D" | tee -a "$D/run.log"
