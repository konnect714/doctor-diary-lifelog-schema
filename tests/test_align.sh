#!/usr/bin/env bash
# Smoke test for scripts/align_to_grid.py
# Creates synthetic data, runs alignment, checks output shapes.
set -euo pipefail

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "[test] Creating synthetic CGM and meal data in $TMPDIR"

python3 <<EOF
import json, math
from datetime import datetime, timedelta, timezone

kst = timezone(timedelta(hours=9))
start = datetime(2026, 4, 16, 6, 0, tzinfo=kst)

records = []
for i in range(48):
    t = start + timedelta(minutes=5*i)
    mod = t.hour*60 + t.minute
    meal_delta = (t - datetime(2026,4,16,7,30,tzinfo=kst)).total_seconds()/60
    if meal_delta < 0: g = 100
    elif meal_delta < 45: g = 100 + meal_delta*1.8
    elif meal_delta < 120: g = 180 - (meal_delta-45)*0.8
    else: g = 120 - (meal_delta-120)*0.1
    g = round(g)
    records.append({
        "schema_version":"1.0.0",
        "record_id": f"cgm_u_test_{t.strftime('%Y%m%dT%H%M%S')}",
        "user_id_hash":"u_test",
        "timestamp": t.isoformat(),
        "local_timezone":"Asia/Seoul",
        "minute_of_day": mod,
        "sin_time": math.sin(2*math.pi*mod/1440),
        "cos_time": math.cos(2*math.pi*mod/1440),
        "day_of_week": t.weekday(),
        "glucose_mgdl": float(g),
        "glucose_token": max(0, min(259, g-40)),
        "missing_mask": 0,
        "missing_reason": None,
        "quality_flag":"normal",
        "device_model":"dexcom_g7"
    })

with open("$TMPDIR/cgm.jsonl","w") as f:
    for r in records:
        f.write(json.dumps(r)+"\n")

meal = {
    "schema_version":"1.0.0",
    "event_id":"meal_test001",
    "user_id_hash":"u_test",
    "event_start":"2026-04-16T07:30:00+09:00",
    "event_end":"2026-04-16T07:45:00+09:00",
    "recorded_at":"2026-04-16T07:35:00+09:00",
    "meal_type":"breakfast",
    "nutrients":{"kcal":520,"carb_g":75.0,"protein_g":22.0,"fat_g":15.0,"fiber_g":6.0},
    "input_method":"manual",
    "confidence":0.9
}
with open("$TMPDIR/diet.jsonl","w") as f:
    f.write(json.dumps(meal)+"\n")

open("$TMPDIR/exercise.jsonl","w").close()
EOF

echo "[test] Running align_to_grid.py"
python scripts/align_to_grid.py \
    --cgm "$TMPDIR/cgm.jsonl" \
    --diet "$TMPDIR/diet.jsonl" \
    --exercise "$TMPDIR/exercise.jsonl" \
    --start "2026-04-16T06:00:00+09:00" \
    --end "2026-04-16T10:00:00+09:00" \
    --out "$TMPDIR/out.npz"

echo "[test] Verifying output"
python3 <<EOF
import numpy as np
import sys

d = np.load("$TMPDIR/out.npz")
expected_channels = {
    "glucose_mgdl", "glucose_token", "cgm_mask",
    "sin_time", "cos_time", "day_of_week",
    "diet_active", "diet_minutes_since_start", "diet_carb_cum_2h", "diet_kcal_active",
    "exercise_active", "exercise_met", "exercise_met_min_cum_1h", "exercise_minutes_since_end",
    "grid_timestamps"
}
actual = set(d.keys())
missing = expected_channels - actual
if missing:
    print(f"[FAIL] Missing channels: {missing}", file=sys.stderr)
    sys.exit(1)

# All channels should have 48 steps
for k in expected_channels:
    if d[k].shape[0] != 48:
        print(f"[FAIL] {k} has shape {d[k].shape}, expected (48,)", file=sys.stderr)
        sys.exit(1)

# Diet should be active at step 18 (07:30)
if not d["diet_active"][18]:
    print("[FAIL] Diet should be active at step 18 (07:30)", file=sys.stderr)
    sys.exit(1)

# minutes_since_start should be 60 at step 30 (08:30, 1 hr after meal)
if abs(d["diet_minutes_since_start"][30] - 60) > 0.01:
    print(f"[FAIL] minutes_since_start at step 30 = {d['diet_minutes_since_start'][30]}, expected 60", file=sys.stderr)
    sys.exit(1)

# Carb cum should be 75g around/after meal
if d["diet_carb_cum_2h"][30] != 75.0:
    print(f"[FAIL] diet_carb_cum_2h at step 30 = {d['diet_carb_cum_2h'][30]}, expected 75", file=sys.stderr)
    sys.exit(1)

print("[PASS] All alignment checks passed")
EOF

echo "[test] Done."
