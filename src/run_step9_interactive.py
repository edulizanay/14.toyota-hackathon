# ABOUTME: Step 9: Create interactive driver comparison dashboard
# ABOUTME: Dropdown menu to select and compare any driver against fastest reference

import pandas as pd
from pathlib import Path
from visualization import create_interactive_dashboard

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
BRAKE_EVENTS_CSV = BASE_DIR / "data" / "brake-analysis" / "brake_events.csv"
DRIVER_SUMMARY_CSV = BASE_DIR / "data" / "consistency-scores" / "driver_summary.csv"
OUTPUT_HTML = BASE_DIR / "data" / "visualizations" / "final_interactive.html"


def main():
    print("=" * 80)
    print("STEP 9: Interactive Driver Comparison Dashboard")
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

    # Identify fastest driver as reference
    print("Identifying reference driver...")
    fastest = (
        driver_summary.dropna(subset=["fastest_lap_seconds"])
        .sort_values("fastest_lap_seconds")
        .iloc[0]
    )
    reference_vehicle = int(fastest["vehicle_number"])
    print(f"✓ Reference driver: #{reference_vehicle}")
    print(f"  Lap time: {fastest['fastest_lap_time']}")
    print()

    # Create interactive dashboard
    print("Creating interactive dashboard...")
    print("=" * 80)
    create_interactive_dashboard(
        telemetry_df=telemetry,
        brake_events_df=brake_events,
        driver_summary_df=driver_summary,
        reference_vehicle_number=reference_vehicle,
        output_path=OUTPUT_HTML,
    )

    print("=" * 80)
    print("✓ STEP 9 COMPLETE")
    print(f"✓ Interactive dashboard saved to: {OUTPUT_HTML}")
    print("✓ Open in browser and use dropdown to compare drivers")
    print("=" * 80)


if __name__ == "__main__":
    main()
