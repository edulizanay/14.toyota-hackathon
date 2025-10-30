# ABOUTME: Step 8: Create reference driver visualization
# ABOUTME: Shows fastest driver's brake points as gray reference clusters

import pandas as pd
from pathlib import Path
from visualization import plot_reference_driver

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
BRAKE_EVENTS_CSV = BASE_DIR / "data" / "brake-analysis" / "brake_events.csv"
DRIVER_SUMMARY_CSV = BASE_DIR / "data" / "consistency-scores" / "driver_summary.csv"
OUTPUT_HTML = BASE_DIR / "data" / "visualizations" / "step8_reference_driver.html"


def main():
    print("=" * 80)
    print("STEP 8: Reference Driver Visualization")
    print("=" * 80)
    print()

    # Load data
    print("Loading data...")
    telemetry = pd.read_csv(TELEMETRY_PATH)
    brake_events = pd.read_csv(BRAKE_EVENTS_CSV)
    driver_summary = pd.read_csv(DRIVER_SUMMARY_CSV)
    print(f"✓ Loaded telemetry: {len(telemetry):,} rows")
    print(f"✓ Loaded brake events: {len(brake_events):,} events")
    print(f"✓ Loaded driver summary: {len(driver_summary)} drivers")
    print()

    # Identify fastest driver
    print("Identifying fastest driver...")
    fastest = (
        driver_summary.dropna(subset=["fastest_lap_seconds"])
        .sort_values("fastest_lap_seconds")
        .iloc[0]
    )
    reference_vehicle = int(fastest["vehicle_number"])
    print(f"✓ Fastest driver: #{reference_vehicle}")
    print(f"  Lap time: {fastest['fastest_lap_time']}")
    print(f"  Avg dispersion: {fastest['avg_dispersion_meters']:.2f}m")
    print()

    # Create visualization
    print("Creating reference visualization...")
    print("=" * 80)
    plot_reference_driver(
        telemetry_df=telemetry,
        brake_events_df=brake_events,
        reference_vehicle_number=reference_vehicle,
        output_path=OUTPUT_HTML,
    )

    print("=" * 80)
    print("✓ STEP 8 COMPLETE")
    print(f"✓ Reference visualization saved to: {OUTPUT_HTML}")
    print("✓ Open in browser to review")
    print("=" * 80)


if __name__ == "__main__":
    main()
