#!/usr/bin/env python3
"""
MET Value Mapping for Physical Activities
신체활동별 MET 값 매핑 (신체활동 2011 Compendium)

Maps activity_type enum values from schema_exercise.json to default MET values
from the Compendium of Physical Activities 2011.

Reference: Ainsworth et al. (2011)
"2011 Compendium of Physical Activities: a second update of codes and MET values"
https://doi.org/10.1097/01.mej.0000385875.87860.40
"""

from typing import Optional, Dict

# Activity → MET value mapping (Compendium 2011)
# 활동 → MET 값 매핑 (신체활동 2011 Compendium)
MET_MAPPING: Dict[str, float] = {
    # Ambulation (걷기)
    "walking": 3.5,          # 3.5 mph (5.6 km/h), moderate pace
    "running": 9.8,          # 6 mph (9.7 km/h) jogging

    # Cycling (자전거)
    "cycling": 7.5,          # 12-14 mph (19-23 km/h), moderate pace

    # Outdoor recreation (야외활동)
    "hiking": 6.0,           # Hiking uphill
    "climbing": 8.0,         # Rock climbing (rock climbing gym)

    # Water activities (수상활동)
    "swimming": 8.0,         # Swimming, freestyle, moderate effort

    # Mind-body exercises (명상/요가)
    "yoga": 2.5,             # Yoga, Hatha
    "pilates": 3.0,          # Pilates, general

    # Strength & resistance (근력운동)
    "weight_training": 6.0,  # Weight training, general
    "home_workout": 4.0,     # General home exercise

    # Machine cardio (기계 유산소)
    "elliptical": 6.0,       # Elliptical trainer, moderate effort

    # Sports (스포츠)
    "dancing": 5.5,          # Dancing, ballroom, slow
    "golf": 4.5,             # Golf, walking, carrying clubs
    "tennis": 7.3,           # Tennis, singles, moderate
    "badminton": 4.5,        # Badminton, competitive

    # Daily living (일상활동)
    "daily_activity": 2.0,   # Light activity, light household chores

    # Unknown/Other (기타)
    "other": 3.5,            # Default generic activity
}


def get_default_met(activity_type: str) -> Optional[float]:
    """
    Get default MET value for an activity type.
    활동 유형에 대한 기본 MET 값 조회

    Args:
        activity_type: Activity type from schema_exercise.json enum

    Returns:
        MET value (float) or None if not found.
        Unknown activities default to "other" → 3.5 MET
    """
    if activity_type in MET_MAPPING:
        return MET_MAPPING[activity_type]

    # Fallback to generic activity
    return MET_MAPPING.get("other", 3.5)


def get_all_activities() -> Dict[str, float]:
    """
    Get all supported activities and their MET values.
    모든 지원 활동과 MET 값 조회

    Returns:
        Dictionary mapping activity_type → MET value
    """
    return MET_MAPPING.copy()


def validate_activity_type(activity_type: str) -> bool:
    """
    Check if an activity type is valid and has a MET mapping.
    활동 유형이 유효하고 MET 매핑이 있는지 확인

    Args:
        activity_type: Activity type to validate

    Returns:
        True if valid, False otherwise
    """
    return activity_type in MET_MAPPING


# Category grouping for analysis
ACTIVITY_CATEGORIES: Dict[str, list] = {
    "ambulation": ["walking", "running"],
    "cycling": ["cycling"],
    "outdoor_recreation": ["hiking", "climbing"],
    "water_activities": ["swimming"],
    "mind_body": ["yoga", "pilates"],
    "strength_resistance": ["weight_training", "home_workout"],
    "machine_cardio": ["elliptical"],
    "sports": ["dancing", "golf", "tennis", "badminton"],
    "daily_living": ["daily_activity"],
    "other": ["other"],
}


def get_activity_category(activity_type: str) -> Optional[str]:
    """
    Get the category for an activity type.
    활동 유형의 카테고리 조회

    Args:
        activity_type: Activity type

    Returns:
        Category name or None if not found
    """
    for category, activities in ACTIVITY_CATEGORIES.items():
        if activity_type in activities:
            return category
    return None


def get_activities_by_met_range(min_met: float, max_met: float) -> Dict[str, float]:
    """
    Get activities within a MET range.
    MET 범위 내의 활동 조회

    Args:
        min_met: Minimum MET value (inclusive)
        max_met: Maximum MET value (inclusive)

    Returns:
        Dictionary of activities within range
    """
    return {
        activity: met
        for activity, met in MET_MAPPING.items()
        if min_met <= met <= max_met
    }


if __name__ == "__main__":
    # Example usage
    print("Doctor Diary MET Mapping")
    print("=" * 50)
    print(f"\nTotal activities: {len(MET_MAPPING)}")
    print("\nActivity → MET Value mapping:")
    print("-" * 50)
    for activity, met in sorted(MET_MAPPING.items(), key=lambda x: x[1], reverse=True):
        category = get_activity_category(activity)
        print(f"  {activity:20} → {met:4.1f} MET  [{category}]")

    print("\n" + "=" * 50)
    print("Examples:")
    print(f"  walking: {get_default_met('walking')} MET")
    print(f"  running: {get_default_met('running')} MET")
    print(f"  yoga: {get_default_met('yoga')} MET")
    print(f"  tennis: {get_default_met('tennis')} MET")
    print(f"  unknown: {get_default_met('unknown')} MET (fallback)")
