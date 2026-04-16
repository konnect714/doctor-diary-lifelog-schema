#!/usr/bin/env python3
"""
Doctor Diary App Data Extraction Helper
닥터다이어리 앱 DB → JSON/JSONL 변환 도우미

Usage:
    python extract_from_app.py --type cgm --db-uri "postgresql://..." --output data/cgm.jsonl
    python extract_from_app.py --type diet --db-uri "postgresql://..." --output data/diet.jsonl
    python extract_from_app.py --type exercise --db-uri "postgresql://..." --output data/exercise.jsonl
    python extract_from_app.py --type checkup --db-uri "postgresql://..." --output data/checkup.jsonl
    python extract_from_app.py --all --db-uri "..." --output-dir data/

Features:
- PII scrubbing (HMAC-SHA256 pseudonymization)
- Automatic timestamp normalization (KST offset)
- sin_time/cos_time calculation
- glucose_token computation (260-bin and 460-bin)
- missing_mask generation
- Schema validation on output
- Manifest file generation with SHA-256 hashes
- Progress bar and logging
"""

import argparse
import json
import hashlib
import hmac
import math
import datetime
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

# HMAC secret for PII pseudonymization
# IT team MUST set this to a secure value and keep it secret
HMAC_SECRET = b"REPLACE_WITH_SECURE_SECRET_KEY"


def pseudonymize_user_id(raw_id: str, secret: bytes) -> str:
    """
    HMAC-SHA256 pseudonymization of user ID.
    닥터다이어리 유저 ID를 HMAC-SHA256으로 익명화

    Args:
        raw_id: Original user ID (real PII)
        secret: HMAC secret key

    Returns:
        Hex-encoded hash safe for inclusion in datasets
    """
    if isinstance(raw_id, str):
        raw_id = raw_id.encode("utf-8")
    h = hmac.new(secret, raw_id, hashlib.sha256)
    return h.hexdigest()[:24]


def normalize_timestamp(ts_str: str) -> str:
    """
    Normalize timestamp to ISO 8601 with +09:00 offset (KST).
    타임스탬프를 ISO 8601 포맷 +09:00 (한국시간)으로 정규화

    Args:
        ts_str: Input timestamp string (various formats supported)

    Returns:
        ISO 8601 string with +09:00 offset
    """
    try:
        # Try parsing various formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO with offset
            "%Y-%m-%d %H:%M:%S",     # Datetime without offset
            "%Y-%m-%dT%H:%M:%S",     # ISO without offset
        ]:
            try:
                dt = datetime.datetime.strptime(ts_str.split("+")[0].split("Z")[0].strip(), fmt if "T" in ts_str else "%Y-%m-%d %H:%M:%S")
                break
            except ValueError:
                continue
        else:
            # Fallback: assume naive datetime and add KST offset
            dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

        # Ensure UTC and convert to KST
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        kst = datetime.timezone(datetime.timedelta(hours=9))
        dt_kst = dt.astimezone(kst)
        return dt_kst.isoformat()
    except Exception as e:
        logging.warning(f"Failed to parse timestamp '{ts_str}': {e}. Using as-is.")
        return ts_str


def compute_sin_cos(minute_of_day: int) -> Tuple[float, float]:
    """
    Compute sin and cos for diurnal encoding.
    일주기 인코딩을 위한 sin, cos 계산

    Args:
        minute_of_day: Minutes since midnight (0-1439)

    Returns:
        Tuple of (sin_value, cos_value)
    """
    angle = 2 * math.pi * minute_of_day / 1440.0
    return (math.sin(angle), math.cos(angle))


def compute_glucose_token(glucose_mgdl: Optional[float], bins: int = 260) -> Optional[int]:
    """
    Compute discrete glucose token.
    260-bin tokenization: clip(round(glucose_mgdl) - 40, 0, 259)
    Supports glucose range 40-299 mg/dL.

    포도당 토큰 계산 (260-bin)
    범위: 40-299 mg/dL → 0-259 bins

    Args:
        glucose_mgdl: Raw glucose value in mg/dL
        bins: Number of bins (default 260 for 40-299 range)

    Returns:
        Discrete token (0 to bins-1) or None if glucose is None
    """
    if glucose_mgdl is None:
        return None
    return max(0, min(bins - 1, round(glucose_mgdl) - 40))


def compute_glucose_token_extended(glucose_mgdl: Optional[float]) -> Optional[int]:
    """
    Compute extended glucose token for GluFormer compatibility.
    460-bin tokenization: supports 40-500 mg/dL range.

    확장 토큰화 (460-bin, GluFormer 호환)
    범위: 40-500 mg/dL → 0-459 bins

    Args:
        glucose_mgdl: Raw glucose value in mg/dL

    Returns:
        Discrete token (0 to 459) or None if glucose is None
    """
    return compute_glucose_token(glucose_mgdl, bins=460)


def generate_missing_mask(glucose_value: Optional[float]) -> Tuple[int, Optional[str]]:
    """
    Generate missing_mask and reason.
    누락된 값에 대해 mask와 reason 생성

    Args:
        glucose_value: Glucose value (None if missing)

    Returns:
        Tuple of (mask, reason). mask=0 if present, 1 if missing.
    """
    if glucose_value is None:
        return (1, "unknown")
    return (0, None)


class DataExtractor:
    """
    데이터 추출 및 변환을 위한 메인 클래스
    Main extraction and transformation class for lifelog data.
    """

    def __init__(self, db_uri: str, hmac_secret: bytes, output_dir: Path):
        self.db_uri = db_uri
        self.hmac_secret = hmac_secret
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def extract_cgm(self, output_path: Optional[Path] = None) -> Tuple[int, str]:
        """
        Extract CGM records from database.
        CGM 기록 추출

        Returns:
            Tuple of (record_count, output_file_path)
        """
        if output_path is None:
            output_path = self.output_dir / "cgm.jsonl"

        # SQL TEMPLATE (IT team fills in with actual query)
        sql_query = """
        -- SQL TEMPLATE: Replace with actual Doctor Diary DB query
        -- SELECT
        --   record_id,
        --   user_id,
        --   timestamp,
        --   glucose_mgdl,
        --   device_model,
        --   missing_reason
        -- FROM cgm_records
        -- WHERE timestamp BETWEEN ? AND ?
        -- ORDER BY timestamp
        """

        self.logger.info(f"Extracting CGM data to {output_path}")
        records = self._execute_query(sql_query, "CGM")
        count = self._transform_cgm_records(records, output_path)
        return count, str(output_path)

    def extract_diet(self, output_path: Optional[Path] = None) -> Tuple[int, str]:
        """
        Extract diet/meal records from database.
        식사 기록 추출
        """
        if output_path is None:
            output_path = self.output_dir / "diet.jsonl"

        sql_query = """
        -- SQL TEMPLATE: Replace with actual Doctor Diary DB query
        -- SELECT
        --   event_id,
        --   user_id,
        --   event_start,
        --   meal_type,
        --   kcal,
        --   carb_g,
        --   protein_g,
        --   fat_g
        -- FROM meal_events
        -- ORDER BY event_start
        """

        self.logger.info(f"Extracting diet data to {output_path}")
        records = self._execute_query(sql_query, "DIET")
        count = self._transform_diet_records(records, output_path)
        return count, str(output_path)

    def extract_exercise(self, output_path: Optional[Path] = None) -> Tuple[int, str]:
        """
        Extract exercise/activity records from database.
        운동 기록 추출
        """
        if output_path is None:
            output_path = self.output_dir / "exercise.jsonl"

        sql_query = """
        -- SQL TEMPLATE: Replace with actual Doctor Diary DB query
        -- SELECT
        --   event_id,
        --   user_id,
        --   event_start,
        --   event_end,
        --   activity_type,
        --   intensity,
        --   duration_min,
        --   input_method,
        --   device_source
        -- FROM exercise_events
        -- ORDER BY event_start
        """

        self.logger.info(f"Extracting exercise data to {output_path}")
        records = self._execute_query(sql_query, "EXERCISE")
        count = self._transform_exercise_records(records, output_path)
        return count, str(output_path)

    def extract_checkup(self, output_path: Optional[Path] = None) -> Tuple[int, str]:
        """
        Extract checkup/clinical visit records from database.
        검진/방문 기록 추출
        """
        if output_path is None:
            output_path = self.output_dir / "checkup.jsonl"

        sql_query = """
        -- SQL TEMPLATE: Replace with actual Doctor Diary DB query
        -- SELECT
        --   checkup_id,
        --   user_id,
        --   visit_date,
        --   hba1c,
        --   glucose_fasting
        -- FROM checkup_records
        -- ORDER BY visit_date
        """

        self.logger.info(f"Extracting checkup data to {output_path}")
        records = self._execute_query(sql_query, "CHECKUP")
        count = self._transform_checkup_records(records, output_path)
        return count, str(output_path)

    def _execute_query(self, sql_template: str, record_type: str) -> List[Dict[str, Any]]:
        """
        Execute database query (placeholder).
        실제 DB 쿼리 실행 (플레이스홀더)

        Note: IT team must implement actual database connection
        """
        self.logger.warning(f"[TEMPLATE] {record_type} query not implemented. Replace SQL_TEMPLATE in code.")
        return []

    def _transform_cgm_records(self, records: List[Dict], output_path: Path) -> int:
        """Transform raw CGM records to schema format."""
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                try:
                    user_id_hash = pseudonymize_user_id(rec.get("user_id", ""), self.hmac_secret)
                    ts = normalize_timestamp(rec.get("timestamp", ""))
                    dt = datetime.datetime.fromisoformat(ts)
                    minute_of_day = dt.hour * 60 + dt.minute
                    sin_val, cos_val = compute_sin_cos(minute_of_day)
                    glucose = rec.get("glucose_mgdl")
                    mask, reason = generate_missing_mask(glucose)

                    transformed = {
                        "schema_version": "1.0.0",
                        "record_id": rec.get("record_id"),
                        "user_id_hash": user_id_hash,
                        "timestamp": ts,
                        "local_timezone": "Asia/Seoul",
                        "minute_of_day": minute_of_day,
                        "sin_time": sin_val,
                        "cos_time": cos_val,
                        "day_of_week": dt.weekday(),
                        "glucose_mgdl": glucose,
                        "glucose_token": compute_glucose_token(glucose),
                        "glucose_token_extended": compute_glucose_token_extended(glucose),
                        "missing_mask": mask,
                        "missing_reason": reason,
                        "quality_flag": "normal",
                        "device_model": rec.get("device_model", "unknown"),
                        "device_serial_hash": None,
                        "sensor_session_id": rec.get("sensor_session_id"),
                        "sensor_day": rec.get("sensor_day"),
                        "rate_of_change_mgdl_per_min": rec.get("roc"),
                        "cgm_data_completeness": rec.get("completeness"),
                        "imputation_applied": False,
                        "imputation_method": None,
                    }
                    f.write(json.dumps(transformed, ensure_ascii=False) + "\n")
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to transform CGM record: {e}")
        return count

    def _transform_diet_records(self, records: List[Dict], output_path: Path) -> int:
        """Transform raw diet records to schema format."""
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                try:
                    user_id_hash = pseudonymize_user_id(rec.get("user_id", ""), self.hmac_secret)
                    event_start = normalize_timestamp(rec.get("event_start", ""))

                    transformed = {
                        "schema_version": "1.0.0",
                        "event_id": rec.get("event_id"),
                        "user_id_hash": user_id_hash,
                        "event_start": event_start,
                        "event_end": normalize_timestamp(rec.get("event_end", "")) if rec.get("event_end") else None,
                        "recorded_at": normalize_timestamp(rec.get("recorded_at", "")) if rec.get("recorded_at") else None,
                        "meal_type": rec.get("meal_type", "unknown"),
                        "nutrients": {
                            "kcal": rec.get("kcal"),
                            "carb_g": rec.get("carb_g"),
                            "sugar_g": rec.get("sugar_g"),
                            "protein_g": rec.get("protein_g"),
                            "fat_g": rec.get("fat_g"),
                            "fiber_g": rec.get("fiber_g"),
                            "sodium_mg": rec.get("sodium_mg"),
                            "cholesterol_mg": rec.get("cholesterol_mg"),
                            "glycemic_index": rec.get("glycemic_index"),
                            "glycemic_load": rec.get("glycemic_load"),
                            "_missing_fields": rec.get("missing_fields", []),
                        },
                        "foods": rec.get("foods", []),
                        "free_text_description": rec.get("description"),
                        "photo_id": rec.get("photo_id"),
                        "input_method": rec.get("input_method", "manual"),
                        "confidence": rec.get("confidence", 0.8),
                        "quality_flag": "normal",
                        "postprandial_peak_mgdl": rec.get("peak_glucose"),
                        "time_to_peak_minutes": rec.get("time_to_peak"),
                        "time_to_baseline_minutes": rec.get("time_to_baseline"),
                    }
                    f.write(json.dumps(transformed, ensure_ascii=False) + "\n")
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to transform diet record: {e}")
        return count

    def _transform_exercise_records(self, records: List[Dict], output_path: Path) -> int:
        """Transform raw exercise records to schema format."""
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                try:
                    user_id_hash = pseudonymize_user_id(rec.get("user_id", ""), self.hmac_secret)
                    event_start = normalize_timestamp(rec.get("event_start", ""))
                    event_end = normalize_timestamp(rec.get("event_end", "")) if rec.get("event_end") else None

                    transformed = {
                        "schema_version": "1.0.0",
                        "event_id": rec.get("event_id"),
                        "user_id_hash": user_id_hash,
                        "event_start": event_start,
                        "event_end": event_end,
                        "duration_min": rec.get("duration_min", 0),
                        "activity_type": rec.get("activity_type", "other"),
                        "met_code": rec.get("met_code"),
                        "met_value": rec.get("met_value"),
                        "intensity": rec.get("intensity", "unknown"),
                        "metrics": {
                            "steps": rec.get("steps"),
                            "distance_m": rec.get("distance_m"),
                            "kcal_burned": rec.get("kcal_burned"),
                            "hr_avg_bpm": rec.get("hr_avg_bpm"),
                            "hr_max_bpm": rec.get("hr_max_bpm"),
                            "elevation_gain_m": rec.get("elevation_gain_m"),
                            "pace_min_per_km": rec.get("pace_min_per_km"),
                            "_missing_fields": rec.get("missing_fields", []),
                        },
                        "input_method": rec.get("input_method", "manual"),
                        "device_source": rec.get("device_source"),
                        "confidence": rec.get("confidence", 0.8),
                        "heart_rate_variability_rmssd": rec.get("hrv_rmssd"),
                        "post_exercise_sensitivity_hours": rec.get("post_ex_sensitivity"),
                    }
                    f.write(json.dumps(transformed, ensure_ascii=False) + "\n")
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to transform exercise record: {e}")
        return count

    def _transform_checkup_records(self, records: List[Dict], output_path: Path) -> int:
        """Transform raw checkup records to schema format."""
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                try:
                    user_id_hash = pseudonymize_user_id(rec.get("user_id", ""), self.hmac_secret)

                    transformed = {
                        "schema_version": "1.0.0",
                        "checkup_id": rec.get("checkup_id"),
                        "user_id_hash": user_id_hash,
                        "visit_date": normalize_timestamp(rec.get("visit_date", "")),
                        "clinical_notes": rec.get("notes"),
                        "glucose_fasting": rec.get("glucose_fasting"),
                        "hba1c_percent": rec.get("hba1c"),
                        "blood_pressure_systolic": rec.get("bp_systolic"),
                        "blood_pressure_diastolic": rec.get("bp_diastolic"),
                        "weight_kg": rec.get("weight"),
                        "bmi": rec.get("bmi"),
                        "input_method": "clinical_entry",
                    }
                    f.write(json.dumps(transformed, ensure_ascii=False) + "\n")
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to transform checkup record: {e}")
        return count

    def validate_output(self, data_file: Path, record_type: str) -> bool:
        """
        Validate output file against schema.
        출력 파일을 스키마로 검증

        Uses validate.py from scripts/ directory.
        """
        try:
            import subprocess
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parent / "validate.py"),
                    str(data_file),
                    "--type",
                    record_type,
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                self.logger.info(f"✓ Validation passed for {data_file.name}")
                return True
            else:
                self.logger.error(f"✗ Validation failed for {data_file.name}")
                print(result.stdout.decode())
                return False
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def generate_manifest(self, output_dir: Path) -> Dict[str, Any]:
        """
        Generate manifest.json with file hashes.
        파일 해시를 포함한 manifest.json 생성
        """
        manifest = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "files": {},
        }

        for f in output_dir.glob("*.jsonl"):
            sha256_hash = hashlib.sha256(f.read_bytes()).hexdigest()
            manifest["files"][f.name] = {
                "path": f.name,
                "size_bytes": f.stat().st_size,
                "sha256": sha256_hash,
            }

        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Manifest generated: {manifest_path}")
        return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Doctor Diary data extraction helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract single type
  python extract_from_app.py --type cgm --db-uri "postgresql://user:pass@localhost/doctordiary" --output data/cgm.jsonl

  # Extract all types
  python extract_from_app.py --all --db-uri "postgresql://..." --output-dir data/
        """,
    )

    parser.add_argument(
        "--type",
        choices=["cgm", "diet", "exercise", "checkup"],
        help="Data type to extract",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Extract all data types",
    )
    parser.add_argument(
        "--db-uri",
        required=True,
        help="Database URI (postgresql://...)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (.jsonl)",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory for --all mode (default: data/)",
    )
    parser.add_argument(
        "--secret",
        default=None,
        help="HMAC secret for pseudonymization (overrides HMAC_SECRET)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation of output",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Skip manifest.json generation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Validate arguments
    if not args.all and not args.type:
        parser.error("Must specify --type or --all")
    if args.type and args.output is None:
        parser.error("--type requires --output")

    # Setup extractor
    secret = (args.secret or HMAC_SECRET).encode() if isinstance(args.secret or HMAC_SECRET, str) else (args.secret or HMAC_SECRET)
    output_dir = Path(args.output_dir)
    extractor = DataExtractor(args.db_uri, secret, output_dir)

    # Run extraction
    results = {}
    try:
        if args.all:
            for data_type in ["cgm", "diet", "exercise", "checkup"]:
                count, path = getattr(extractor, f"extract_{data_type}")()
                results[data_type] = {"count": count, "path": path}

                if not args.no_validate:
                    extractor.validate_output(Path(path), data_type)

                logger.info(f"✓ Extracted {count} {data_type} records → {path}")
        else:
            count, path = getattr(extractor, f"extract_{args.type}")()
            results[args.type] = {"count": count, "path": path}

            if not args.no_validate:
                extractor.validate_output(Path(path), args.type)

            logger.info(f"✓ Extracted {count} {args.type} records → {path}")

        if not args.no_manifest:
            extractor.generate_manifest(output_dir)

        print("\n=== EXTRACTION COMPLETE ===")
        for dtype, info in results.items():
            print(f"{dtype}: {info['count']} records → {info['path']}")

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
