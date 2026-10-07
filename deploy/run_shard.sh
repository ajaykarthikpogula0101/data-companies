#!/usr/bin/env bash
#
# Run one shard of the full dataset on this VM.
#
#   SHARD_INDEX=0 SHARD_COUNT=5 ./run_shard.sh          # the real run, VM 0 of 5
#   RETRY_FAILURES=1 SHARD_INDEX=0 SHARD_COUNT=5 ./run_shard.sh
#
# SHARD_MODE=interleave (default) gives every VM every Nth row, so all five get
# the same amount of real work. SHARD_MODE=block gives contiguous slices.
#
# Delegates to run_all.py, which computes the shard slice itself and supports
# CSV / TSV / XLSX input. Resume is on by default: companies already present in
# this shard's output CSV are skipped, so restarting never loses or duplicates
# work.
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/job_scraper}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
ENVFILE="${ENVFILE:-$APP_DIR/.env.scraper}"

[[ -f "$ENVFILE" ]] && { set -a; . "$ENVFILE"; set +a; }

SHARD_INDEX="${SHARD_INDEX:-0}"
SHARD_COUNT="${SHARD_COUNT:-5}"
INPUT="${INPUT:-${JOB_SCRAPER_INPUT:-$APP_DIR/data/data_7.7m_405k.csv}}"
OUTDIR="${OUTDIR:-$APP_DIR/output}"
WORKERS="${WORKERS:-${JOB_SCRAPER_WORKERS:-12}}"
SHARD_MODE="${SHARD_MODE:-${JOB_SCRAPER_SHARD_MODE:-interleave}}"
LIMIT="${LIMIT:-0}"

if [[ ! -f "$INPUT" ]]; then
  echo "input not found: $INPUT" >&2; exit 1
fi
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "venv python not found: $VENV_DIR/bin/python -- run azure_ubuntu_setup.sh first" >&2
  exit 1
fi

# Name the output after the machine, so five downloaded files never collide and
# you can always tell which VM produced which rows.
VM_NAME="${VM_NAME:-$(hostname -s 2>/dev/null || hostname)}"
OUTPUT="${OUTPUT:-${JOB_SCRAPER_OUTPUT:-$OUTDIR/${VM_NAME}_shard_${SHARD_INDEX}_of_${SHARD_COUNT}.csv}}"
mkdir -p "$OUTDIR" "$APP_DIR/logs"

ARGS=( --input "$INPUT" --output "$OUTPUT"
       --shard-index "$SHARD_INDEX" --shard-count "$SHARD_COUNT"
       --shard-mode "$SHARD_MODE"
       --workers "$WORKERS" )

# LIMIT caps how many of THIS shard's rows to do; leave it at 0 for the real run.
if (( LIMIT > 0 )); then
  ARGS+=( --limit "$LIMIT" )
fi
[[ -n "${OFFSET:-}" ]] && ARGS+=( --offset "$OFFSET" )
[[ -n "${COUNTRIES:-}" ]] && ARGS+=( --countries "$COUNTRIES" )
[[ "${RETRY_FAILURES:-0}" == "1" ]] && ARGS+=( --retry-failures )
[[ "${NO_RESUME:-0}" == "1" ]] && ARGS+=( --no-resume )
[[ "${VERBOSE:-0}" == "1" ]] && ARGS+=( --verbose )

echo "vm=${VM_NAME}  shard ${SHARD_INDEX}/${SHARD_COUNT} (${SHARD_MODE})  input=$INPUT  workers=$WORKERS"
echo "output: $OUTPUT"

cd "$APP_DIR"
exec "$VENV_DIR/bin/python" "$APP_DIR/run_all.py" "${ARGS[@]}"
