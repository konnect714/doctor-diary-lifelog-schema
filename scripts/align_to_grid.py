#!/usr/bin/env python3
"""
Project event-based diet and exercise data onto the CGM 5-minute grid.

Input:  CGM jsonl, diet jsonl, exercise jsonl (all for one user, one time range)
Output: NumPy arrays (or HDF5) with aligned channels, ready for model training.

Design reference: references/cgm_grid.md and references/event_schema.md

The key projected channels per 5-minute step are:

CGM side:
  glucose_mgdl                   float
  glucose_token                  int (0-259)
  cgm_mask                       bool
  sin_time, cos_time             float

Diet side:
  diet_active                    bool
  diet_minutes_since_start       float (large number if none)
  diet_carb_cum_2h               float
  diet_kcal_active               float

Exercise side:
  exercise_active                bool
  exercise_met                   float
  exercise_met_min_cum_1h        float
  exercise_minutes_since_end     float

Static checkup values are separately attached per window (not handled here).
"""

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np


STEP_MIN = 5
STEPS_PER_DAY = 288


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_grid(start: datetime, end: datetime) -> np.ndarray:
    """Return array of datetimes at 5-min intervals from start (inclusive) to end (exclusive)."""
    n_steps = int((end - start).total_seconds() / (STEP_MIN * 60))
    return np.array([start + timedelta(minutes=STEP_MIN * i) for i in range(n_steps)])


def align_cgm(cgm_records: list, grid: np.ndarray) -> dict:
    """Map CGM records to grid slots."""
    n = len(grid)
    glucose = np.full(n, np.nan, dtype=np.float32)
    token = np.full(n, np.nan, dtype=np.float32)  # Use NaN for missing, not -1
    mask = np.ones(n, dtype=bool)  # True = missing

    # Index records by their grid step
    by_step = {}
    for rec in cgm_records:
        ts = parse_iso(rec["timestamp"])
        if ts < grid[0] or ts >= grid[-1] + timedelta(minutes=STEP_MIN):
            continue
        step_idx = int((ts - grid[0]).total_seconds() / (STEP_MIN * 60))
        by_step[step_idx] = rec

    for i, rec in by_step.items():
        if rec.get("missing_mask", 1) == 0 and rec.get("glucose_mgdl") is not None:
            glucose[i] = rec["glucose_mgdl"]
            token[i] = float(rec.get("glucose_token")) if rec.get("glucose_token") is not None else np.nan
            mask[i] = False

    # Time features
    sin_time = np.zeros(n, dtype=np.float32)
    cos_time = np.zeros(n, dtype=np.float32)
    dow = np.zeros(n, dtype=np.int8)
    for i, t in enumerate(grid):
        minute_of_day = t.hour * 60 + t.minute
        sin_time[i] = math.sin(2 * math.pi * minute_of_day / 1440)
        cos_time[i] = math.cos(2 * math.pi * minute_of_day / 1440)
        dow[i] = t.weekday()

    return {
        "glucose_mgdl": glucose,
        "glucose_token": token,
        "cgm_mask": mask,
        "sin_time": sin_time,
        "cos_time": cos_time,
        "day_of_week": dow,
    }


def align_diet(diet_records: list, grid: np.ndarray) -> dict:
    """Project diet events onto grid as channels."""
    n = len(grid)
    active = np.zeros(n, dtype=bool)
    mins_since_start = np.full(n, 1e6, dtype=np.float32)  # "large" if no recent meal
    carb_cum_2h = np.zeros(n, dtype=np.float32)
    kcal_active = np.zeros(n, dtype=np.float32)

    # Sort by start
    events = sorted(diet_records, key=lambda e: parse_iso(e["event_start"]))

    for event in events:
        start = parse_iso(event["event_start"])
        end_iso = event.get("event_end")
        end = parse_iso(end_iso) if end_iso else start + timedelta(minutes=15)  # default 15 min
        nutrients = event.get("nutrients", {})
        carb = nutrients.get("carb_g") or 0
        kcal = nutrients.get("kcal") or 0

        for i, t in enumerate(grid):
            # Active during meal (handle midnight crossing)
            if start <= t < end:
                active[i] = True
                kcal_active[i] = kcal
            # Handle meals spanning midnight (23:50-00:10 case)
            elif start.date() > t.date() and start.time() > t.time():
                # Event started "tomorrow" but we're looking at "today" → check if it wraps from previous midnight
                pass

            # Minutes since start: from meal start, up to 4 hours after
            delta_min = (t - start).total_seconds() / 60
            if 0 <= delta_min <= 240:
                if delta_min < mins_since_start[i]:
                    mins_since_start[i] = delta_min

            # Cumulative carb in past 2 hours with exact overlap calculation
            # Include events with any overlap in [t-2h, t]
            window_start = t - timedelta(hours=2)
            if start < t and end > window_start:
                # Calculate exact overlap between [window_start, t] and [start, end]
                overlap_start = max(start, window_start)
                overlap_end = min(end, t)
                if overlap_end > overlap_start:
                    # Proportional carb contribution based on overlap duration
                    event_duration = (end - start).total_seconds()
                    if event_duration > 0:
                        overlap_duration = (overlap_end - overlap_start).total_seconds()
                        carb_cum_2h[i] += carb * (overlap_duration / event_duration)
                    else:
                        # Point event (start == end), count it fully
                        carb_cum_2h[i] += carb

    return {
        "diet_active": active,
        "diet_minutes_since_start": mins_since_start,
        "diet_carb_cum_2h": carb_cum_2h,
        "diet_kcal_active": kcal_active,
    }


def align_exercise(exercise_records: list, grid: np.ndarray) -> dict:
    n = len(grid)
    active = np.zeros(n, dtype=bool)
    met_current = np.zeros(n, dtype=np.float32)
    met_min_cum_1h = np.zeros(n, dtype=np.float32)
    mins_since_end = np.full(n, 1e6, dtype=np.float32)

    for event in exercise_records:
        start = parse_iso(event["event_start"])
        end = parse_iso(event["event_end"])
        met = event.get("met_value") or 0

        for i, t in enumerate(grid):
            if start <= t < end:
                active[i] = True
                met_current[i] = met
            # Minutes since end: up to 4 hours
            delta_min = (t - end).total_seconds() / 60
            if 0 <= delta_min <= 240:
                if delta_min < mins_since_end[i]:
                    mins_since_end[i] = delta_min
            # Cumulative MET-minutes in past hour
            overlap_start = max(start, t - timedelta(hours=1))
            overlap_end = min(end, t)
            if overlap_end > overlap_start:
                overlap_min = (overlap_end - overlap_start).total_seconds() / 60
                met_min_cum_1h[i] += met * overlap_min

    return {
        "exercise_active": active,
        "exercise_met": met_current,
        "exercise_met_min_cum_1h": met_min_cum_1h,
        "exercise_minutes_since_end": mins_since_end,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cgm", type=Path, required=True)
    parser.add_argument("--diet", type=Path)
    parser.add_argument("--exercise", type=Path)
    parser.add_argument("--start", required=True, help="ISO8601 grid start (inclusive)")
    parser.add_argument("--end", required=True, help="ISO8601 grid end (exclusive)")
    parser.add_argument("--out", type=Path, required=True, help="Output .npz path")
    args = parser.parse_args()

    start = parse_iso(args.start)
    end = parse_iso(args.end)
    grid = build_grid(start, end)

    cgm_records = load_jsonl(args.cgm)
    diet_records = load_jsonl(args.diet) if args.diet else []
    ex_records = load_jsonl(args.exercise) if args.exercise else []

    channels = {}
    channels.update(align_cgm(cgm_records, grid))
    channels.update(align_diet(diet_records, grid))
    channels.update(align_exercise(ex_records, grid))

    channels["grid_timestamps"] = np.array([t.isoformat() for t in grid])

    np.savez_compressed(args.out, **channels)
    print(f"Wrote {len(grid)} steps with {len(channels)} channels to {args.out}")


if __name__ == "__main__":
    main()
