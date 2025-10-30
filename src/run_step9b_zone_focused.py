# ABOUTME: Step 9b: Zone-focused interactive dashboard
# ABOUTME: Replaces dropdown with horizontal zone pills and auto-zoom per zone

import pandas as pd
from pathlib import Path
from visualization import create_zone_focused_dashboard

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
BRAKE_EVENTS_CSV = BASE_DIR / "data" / "brake-analysis" / "brake_events.csv"
DRIVER_SUMMARY_CSV = BASE_DIR / "data" / "consistency-scores" / "driver_summary.csv"
OUTPUT_HTML = BASE_DIR / "data" / "visualizations" / "final_interactive_v2.html"


def main():
    print("=" * 80)
    print("STEP 9b: Zone-Focused Dashboard")
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

    # Find fastest driver
    print("Identifying fastest driver...")
    fastest = (
        driver_summary.dropna(subset=["fastest_lap_seconds"])
        .sort_values("fastest_lap_seconds")
        .iloc[0]
    )
    reference_vehicle = int(fastest["vehicle_number"])
    print(f"✓ Reference driver: #{reference_vehicle}")
    print(f"  Lap time: {fastest['fastest_lap_time']}")
    print()

    # Create zone-focused dashboard
    print("Creating zone-focused dashboard...")
    print("=" * 80)
    create_zone_focused_dashboard(
        telemetry_df=telemetry,
        brake_events_df=brake_events,
        driver_summary_df=driver_summary,
        reference_vehicle_number=reference_vehicle,
        output_path=OUTPUT_HTML,
    )

    print("=" * 80)
    print("✓ STEP 9b COMPLETE")
    print(f"✓ Saved: {OUTPUT_HTML}")
    print("✓ Open in browser to test zone pills and driver chips")
    print("=" * 80)


if __name__ == "__main__":
    main()
