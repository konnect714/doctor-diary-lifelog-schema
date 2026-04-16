#!/usr/bin/env python3
"""
Validate Doctor Diary lifelog data against the JSON schemas.

Usage:
    python validate.py <data_file.jsonl> --type {cgm|diet|exercise|checkup}
    python validate.py --sample  # validate built-in sample data

Returns nonzero exit code if validation fails.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except ImportError:
    print("ERROR: jsonschema package not installed. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(2)


SCHEMA_DIR = Path(__file__).parent.parent / "assets"

SCHEMA_MAP = {
    "cgm": "schema_cgm.json",
    "diet": "schema_diet.json",
    "exercise": "schema_exercise.json",
    "checkup": "schema_checkup.json",
    "annot_meal": "schema_annot_meal.json",
    "annot_cgm_event": "schema_annot_cgm_event.json",
    "annot_quality": "schema_annot_quality.json",
}


def load_schema(record_type: str) -> dict:
    schema_path = SCHEMA_DIR / SCHEMA_MAP[record_type]
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_record(record: dict, record_type: str, validator: Draft202012Validator) -> list:
    """Validate a single record. Returns list of error messages (empty if valid)."""
    errors = []
    for err in validator.iter_errors(record):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"  at {path}: {err.message}")
    return errors


def extra_semantic_checks(record: dict, record_type: str) -> list:
    """Checks beyond JSON Schema that depend on field relationships."""
    errors = []

    if record_type == "cgm":
        # If missing_mask == 1, missing_reason must be non-null
        if record.get("missing_mask") == 1 and not record.get("missing_reason"):
            errors.append("  missing_mask=1 but missing_reason is null/missing")
        # If missing_mask == 0, glucose_mgdl and glucose_token must be non-null
        if record.get("missing_mask") == 0:
            if record.get("glucose_mgdl") is None:
                errors.append("  missing_mask=0 but glucose_mgdl is null")
            if record.get("glucose_token") is None:
                errors.append("  missing_mask=0 but glucose_token is null")
        # Token consistency
        g = record.get("glucose_mgdl")
        t = record.get("glucose_token")
        if g is not None and t is not None:
            expected = max(0, min(259, round(g) - 40))
            if t != expected:
                errors.append(f"  glucose_token={t} inconsistent with glucose_mgdl={g} (expected {expected})")
        # sin/cos consistency check (sample) - increased tolerance for float32 precision
        import math
        mod = record.get("minute_of_day")
        sin_t = record.get("sin_time")
        cos_t = record.get("cos_time")
        if mod is not None and sin_t is not None and cos_t is not None:
            expected_sin = math.sin(2 * math.pi * mod / 1440)
            expected_cos = math.cos(2 * math.pi * mod / 1440)
            if abs(sin_t - expected_sin) > 1e-3 or abs(cos_t - expected_cos) > 1e-3:
                errors.append(f"  sin_time/cos_time inconsistent with minute_of_day={mod}")

    elif record_type == "diet":
        # Check all nutrient fields for consistency with _missing_fields
        nut = record.get("nutrients", {})
        missing_fields = nut.get("_missing_fields", [])
        for nutrient_field in ["kcal", "carb_g", "sugar_g", "protein_g", "fat_g", "fiber_g",
                               "sodium_mg", "cholesterol_mg", "glycemic_index", "glycemic_load"]:
            if nut.get(nutrient_field) is None and nutrient_field not in missing_fields:
                errors.append(f"  nutrients.{nutrient_field} is null but not listed in _missing_fields")

    elif record_type == "exercise":
        start = record.get("event_start")
        end = record.get("event_end")
        dur = record.get("duration_min")
        if start and end and dur is not None:
            from datetime import datetime
            try:
                d = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60
                if abs(d - dur) > 0.5:
                    errors.append(f"  duration_min={dur} inconsistent with event_start/end ({d:.1f} min)")
            except ValueError:
                pass
        # Validate exercise intensity vs met_value consistency
        intensity = record.get("intensity")
        met_value = record.get("met_value")
        if intensity == "vigorous" and met_value is not None and met_value < 6:
            errors.append(f"  intensity='vigorous' requires met_value >= 6, got {met_value}")

    return errors


def validate_file(path: Path, record_type: str) -> tuple[int, int]:
    """Returns (total_records, error_count)."""
    schema = load_schema(record_type)
    validator = Draft202012Validator(schema)

    total = 0
    errors = 0

    if path.suffix == ".jsonl":
        lines = path.read_text(encoding="utf-8").splitlines()
        records = [(i + 1, json.loads(line)) for i, line in enumerate(lines) if line.strip()]
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            records = list(enumerate(data, 1))
        else:
            records = [(1, data)]

    for lineno, record in records:
        total += 1
        schema_errs = validate_record(record, record_type, validator)
        semantic_errs = extra_semantic_checks(record, record_type)
        all_errs = schema_errs + semantic_errs
        if all_errs:
            errors += 1
            rid = record.get("record_id") or record.get("event_id") or record.get("checkup_id") or f"line_{lineno}"
            print(f"[FAIL] {record_type} {rid}")
            for e in all_errs:
                print(e)

    return total, errors


def validate_sample():
    """Validate the built-in sample files."""
    samples = [
        ("sample_data.json", {
            "cgm_sample": "cgm",
            "cgm_missing_sample": "cgm",
            "diet_sample": "diet",
            "exercise_sample": "exercise",
            "checkup_sample": "checkup",
        }),
        ("sample_annotations.json", {
            "annot_meal_sample": "annot_meal",
            "annot_cgm_event_sample": "annot_cgm_event",
            "annot_quality_sample": "annot_quality",
        }),
    ]
    
    total_errors = 0
    for fname, mapping in samples:
        sample_path = SCHEMA_DIR / fname
        if not sample_path.exists():
            print(f"[SKIP] {fname} not found")
            continue
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        for key, rtype in mapping.items():
            if key not in data:
                print(f"[SKIP] {key} not found in {fname}")
                continue
            schema = load_schema(rtype)
            validator = Draft202012Validator(schema)
            errs = validate_record(data[key], rtype, validator)
            errs += extra_semantic_checks(data[key], rtype)
            # Collect warnings (non-blocking)
            warnings = []
            if rtype == "diet" and data[key].get("event_end") is None:
                warnings.append("  WARNING: event_end is null; pipeline will apply 15-minute default")
            if errs:
                total_errors += 1
                print(f"[FAIL] {key}")
                for e in errs:
                    print(e)
            else:
                print(f"[PASS] {key}")
            for w in warnings:
                print(w)
    
    return total_errors


def main():
    parser = argparse.ArgumentParser(description="Validate Doctor Diary lifelog data")
    parser.add_argument("file", nargs="?", help="Path to .json or .jsonl file")
    parser.add_argument(
        "--type",
        choices=list(SCHEMA_MAP.keys()),
        help="Record type",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Validate the built-in sample_data.json",
    )
    args = parser.parse_args()

    if args.sample:
        errs = validate_sample()
        if errs:
            print(f"\n{errs} sample(s) failed validation.")
            sys.exit(1)
        print("\nAll samples passed.")
        return

    if not args.file or not args.type:
        parser.error("Must provide file and --type, or use --sample")

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)

    total, errors = validate_file(path, args.type)
    print(f"\n{total} records checked, {errors} failed.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
