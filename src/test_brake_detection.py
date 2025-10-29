# ABOUTME: Test script to verify brake detection logic
# ABOUTME: Validates rising-edge detection produces sensible results

import pandas as pd
from pathlib import Path
from data_loaders import calculate_brake_threshold
from brake_detection import detect_brake_events

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"


def main():
    print("=" * 80)
    print("Testing Brake Event Detection")
    print("=" * 80)
    print()

    # Load telemetry
    print("Loading telemetry data...")
    df = pd.read_csv(TELEMETRY_PATH)
    print(f"✓ Loaded {len(df):,} rows")
    print()

    # Calculate threshold
    print("Calculating brake threshold (P5 of positive pressures)...")
    print("-" * 80)
    threshold = calculate_brake_threshold(df, percentile=5)
    print()

    # Detect brake events
    print("Detecting brake onset events...")
    print("-" * 80)
    df_events = detect_brake_events(df, threshold)
    print()

    # Show sample events
    print("Sample brake events (first 10):")
    print(
        df_events.head(10)[
            [
                "vehicle_number",
                "lap",
                "brake_pressure",
                "brake_type",
                "x_meters",
                "y_meters",
            ]
        ]
    )
    print()

    # Statistics per vehicle
    print("Brake events per vehicle:")
    events_per_vehicle = (
        df_events.groupby("vehicle_number").size().sort_values(ascending=False)
    )
    print(events_per_vehicle.head(10))
    print()

    # Expected: ~17 corners × ~27 laps × 20 vehicles ≈ 9,180 events
    # (may be fewer due to incomplete laps, pit entries, etc.)
    expected_min = 5000
    expected_max = 15000

    if expected_min <= len(df_events) <= expected_max:
        print(f"✓ Brake event count looks reasonable: {len(df_events):,} events")
    else:
        print(
            f"⚠️  WARNING: Brake event count may be unexpected: {len(df_events):,} events"
        )
        print(f"   Expected range: {expected_min:,} - {expected_max:,}")

    print()
    print("=" * 80)
    print("✓ BRAKE DETECTION TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
