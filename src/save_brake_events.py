# ABOUTME: Save brake events CSV with zone assignments (Step 6)
# ABOUTME: Creates data/brake-analysis/brake_events.csv for consistency analysis

import pandas as pd
import numpy as np
from pathlib import Path
from brake_detection import detect_brake_events
from corner_detection import assign_to_zones

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
OUTPUT_CSV = BASE_DIR / "data" / "brake-analysis" / "brake_events.csv"


def main():
    print("=" * 80)
    print("STEP 6: Save Brake Events CSV with Zone Assignments")
    print("=" * 80)
    print()

    # Load telemetry
    print("Loading telemetry data...")
    df = pd.read_csv(TELEMETRY_PATH)
    print(f"✓ Loaded {len(df):,} rows")
    print()

    # Calculate P5 threshold
    print("Calculating brake pressure threshold (P5)...")
    all_pressures = pd.concat([df["pbrake_f"], df["pbrake_r"]])
    positive_pressures = all_pressures[all_pressures > 0]
    threshold = np.percentile(positive_pressures, 5)
    print(f"✓ P5 threshold: {threshold:.2f} bar")
    print()

    # Detect brake events
    print("Detecting brake events for all drivers...")
    print("-" * 80)
    brake_events = detect_brake_events(df, threshold)
    print()

    # Filter to racing laps only
    print("Filtering to racing laps only...")
    racing_brake_events = []

    for (vehicle, lap), group in brake_events.groupby(["vehicle_number", "lap"]):
        lap_telemetry = df[(df["vehicle_number"] == vehicle) & (df["lap"] == lap)]

        if len(lap_telemetry) > 0:
            lap_telemetry_sorted = lap_telemetry.sort_values("timestamp")
            dx = np.diff(lap_telemetry_sorted["x_meters"].values)
            dy = np.diff(lap_telemetry_sorted["y_meters"].values)
            lap_distance = np.sum(np.sqrt(dx**2 + dy**2))

            if 3500 <= lap_distance <= 4000:
                racing_brake_events.append(group)

    brake_events_filtered = pd.concat(racing_brake_events, ignore_index=True)
    print(f"✓ Racing lap brake events: {len(brake_events_filtered):,}")
    print()

    # Extract track centerline for projection
    print("Extracting track centerline...")
    vehicle_13 = df[df["vehicle_number"] == 13].copy()
    lap_data = vehicle_13[vehicle_13["lap"] == 18].sort_values("timestamp")
    centerline_x = lap_data["x_meters"].values
    centerline_y = lap_data["y_meters"].values
    print(f"✓ Centerline extracted ({len(centerline_x)} points)")
    print()

    # Assign to zones
    print("Assigning brake events to zones...")
    brake_events_with_zones = assign_to_zones(
        brake_events_filtered, centerline_x, centerline_y
    )
    print("✓ Zone assignments complete")
    print()

    # Print statistics
    print("Zone assignment statistics:")
    total = len(brake_events_with_zones)
    in_zone = brake_events_with_zones["zone_id"].notna().sum()
    out_zone = brake_events_with_zones["zone_id"].isna().sum()
    print(f"  Total brake events: {total:,}")
    print(f"  In zones: {in_zone:,} ({100 * in_zone / total:.1f}%)")
    print(f"  Outside zones: {out_zone:,} ({100 * out_zone / total:.1f}%)")
    print()

    # Print per-zone breakdown
    print("Brake events per zone:")
    for zone_id in sorted(brake_events_with_zones["zone_id"].dropna().unique()):
        count = (brake_events_with_zones["zone_id"] == zone_id).sum()
        print(f"  Zone {int(zone_id)}: {count:,} events")
    print()

    # Convert GPS back to lon/lat for output
    print("Converting coordinates back to lon/lat...")
    # Note: x_meters and y_meters are in UTM (EPSG:32616)
    # For now, we'll keep the meter coordinates and add lon/lat columns
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:32616", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(
        brake_events_with_zones["x_meters"].values,
        brake_events_with_zones["y_meters"].values,
    )
    brake_events_with_zones["longitude"] = lon
    brake_events_with_zones["latitude"] = lat
    print(f"✓ Converted {len(brake_events_with_zones):,} coordinates")
    print()

    # Select and order columns for output
    output_columns = [
        "vehicle_number",
        "lap",
        "timestamp",
        "zone_id",
        "track_distance",
        "x_meters",
        "y_meters",
        "longitude",
        "latitude",
        "pbrake_f",
        "pbrake_r",
        "brake_type",
    ]

    brake_events_output = brake_events_with_zones[output_columns].copy()

    # Save to CSV
    print("Saving brake events CSV...")
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    brake_events_output.to_csv(OUTPUT_CSV, index=False)
    print(f"✓ Saved to: {OUTPUT_CSV}")
    print(f"✓ Total rows: {len(brake_events_output):,}")
    print()

    # Show sample rows
    print("Sample rows (first 5):")
    print(brake_events_output.head().to_string())
    print()

    print("=" * 80)
    print("✓ STEP 6 COMPLETE")
    print(f"✓ Brake events saved to {OUTPUT_CSV}")
    print("=" * 80)


if __name__ == "__main__":
    main()
