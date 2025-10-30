# ABOUTME: Generate visualization of brake points filtered to defined zones only
# ABOUTME: Shows concentrated clusters by removing points outside brake zones

import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from brake_detection import detect_brake_events
from track_rendering import generate_track_outline

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
CORNER_DEFINITIONS_JSON = (
    BASE_DIR / "data" / "brake-analysis" / "corner_definitions.json"
)
CORNER_LABELS_JSON = BASE_DIR / "data" / "gps-tracks" / "corner_labels.json"
PIT_LANE_JSON = BASE_DIR / "data" / "gps-tracks" / "pit_lane.json"
OUTPUT_HTML = BASE_DIR / "data" / "visualizations" / "step5c_filtered_brakes.html"


def project_to_centerline(brake_x, brake_y, centerline_x, centerline_y):
    """Project brake points onto track centerline and return track distances."""
    # Calculate cumulative distance along centerline
    dx = np.diff(centerline_x)
    dy = np.diff(centerline_y)
    segment_lengths = np.sqrt(dx**2 + dy**2)
    cumulative_distance = np.concatenate([[0], np.cumsum(segment_lengths)])

    # For each brake point, find nearest centerline point
    track_distances = []

    for bx, by in zip(brake_x, brake_y):
        distances = np.sqrt((centerline_x - bx) ** 2 + (centerline_y - by) ** 2)
        nearest_idx = np.argmin(distances)
        track_distances.append(cumulative_distance[nearest_idx])

    return np.array(track_distances)


def assign_to_zone(track_distance, brake_zones):
    """Assign a track distance to a brake zone (or None if outside all zones)."""
    for zone in brake_zones:
        if zone["start_distance_m"] <= track_distance <= zone["end_distance_m"]:
            return zone["zone_id"]
    return None


def main():
    print("=" * 80)
    print("STEP 5c: Filtered Brake Points (Zones Only)")
    print("=" * 80)
    print()

    # Load brake zones
    print("Loading brake zones...")
    with open(CORNER_DEFINITIONS_JSON, "r") as f:
        brake_zones = json.load(f)
    print(f"✓ Loaded {len(brake_zones)} brake zones")
    for zone in brake_zones:
        print(
            f"  Zone {zone['zone_id']}: {zone['start_distance_m']}-{zone['end_distance_m']}m"
        )
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

    # Extract track centerline
    print("Extracting track centerline...")
    vehicle_13 = df[df["vehicle_number"] == 13].copy()
    lap_data = vehicle_13[vehicle_13["lap"] == 18].sort_values("timestamp")
    centerline_x = lap_data["x_meters"].values
    centerline_y = lap_data["y_meters"].values
    print(f"✓ Centerline extracted ({len(centerline_x)} points)")
    print()

    # Project brake points to track distance
    print("Projecting brake points to track distance...")
    brake_track_distances = project_to_centerline(
        brake_events_filtered["x_meters"].values,
        brake_events_filtered["y_meters"].values,
        centerline_x,
        centerline_y,
    )
    brake_events_filtered["track_distance"] = brake_track_distances
    print(f"✓ Projected {len(brake_track_distances):,} brake points")
    print()

    # Assign to zones
    print("Assigning brake points to zones...")
    brake_events_filtered["zone_id"] = brake_events_filtered["track_distance"].apply(
        lambda d: assign_to_zone(d, brake_zones)
    )

    # Filter to only points within zones
    in_zone = brake_events_filtered[brake_events_filtered["zone_id"].notna()].copy()
    print(f"✓ Brake points before filtering: {len(brake_events_filtered):,}")
    print(f"✓ Brake points in zones: {len(in_zone):,}")
    print(f"✓ Removed: {len(brake_events_filtered) - len(in_zone):,} points")
    print()

    # Print breakdown by zone
    print("Brake points per zone:")
    for zone_id in sorted(in_zone["zone_id"].unique()):
        count = len(in_zone[in_zone["zone_id"] == zone_id])
        zone_info = next(z for z in brake_zones if z["zone_id"] == zone_id)
        print(
            f"  Zone {zone_id} ({zone_info['start_distance_m']}-{zone_info['end_distance_m']}m): {count:,} points"
        )
    print()

    # Generate track outline
    print("Generating track outline...")
    print("-" * 80)
    x_smooth, y_smooth, fig = generate_track_outline(
        df,
        vehicle_number=13,
        lap_number=None,
        resample_step_m=2.0,
        spike_threshold_m=10.0,
        savgol_window=31,
        savgol_poly=3,
        wrap_count=25,
    )
    print()

    # Define colors for each zone
    zone_colors = [
        "#FF6B6B",  # Red
        "#4ECDC4",  # Teal
        "#45B7D1",  # Light blue
        "#96CEB4",  # Sage green
        "#FFEAA7",  # Yellow
        "#DDA15E",  # Orange
        "#C77DFF",  # Purple
        "#06FFA5",  # Mint
    ]

    # Overlay filtered brake points colored by zone
    print("Overlaying filtered brake points...")
    print("-" * 80)

    for zone_id in sorted(in_zone["zone_id"].unique()):
        zone_data = in_zone[in_zone["zone_id"] == zone_id]
        zone_info = next(z for z in brake_zones if z["zone_id"] == zone_id)
        color = zone_colors[int(zone_id) - 1]

        fig.add_trace(
            go.Scatter(
                x=zone_data["x_meters"],
                y=zone_data["y_meters"],
                mode="markers",
                marker=dict(
                    size=5,
                    color=color,
                    opacity=0.6,
                    line=dict(color="rgba(255, 255, 255, 0.3)", width=0.5),
                ),
                name=f"Zone {zone_id}",
                hovertemplate=(
                    f"Zone {zone_id}<br>"
                    + "x: %{x:.1f}m<br>y: %{y:.1f}m<br><extra></extra>"
                ),
            )
        )

    print(f"✓ Added {len(in_zone):,} brake points colored by zone")
    print()

    # Load and overlay pit lane
    print("Loading pit lane...")
    if PIT_LANE_JSON.exists():
        with open(PIT_LANE_JSON, "r") as f:
            pit_lane_data = json.load(f)

        centerline = pit_lane_data["centerline"]
        pit_x = [p["x_meters"] for p in centerline]
        pit_y = [p["y_meters"] for p in centerline]

        fig.add_trace(
            go.Scatter(
                x=pit_x,
                y=pit_y,
                mode="lines",
                line=dict(color="rgba(255, 255, 100, 0.6)", width=3, dash="dash"),
                name="Pit Lane",
                hoverinfo="skip",
            )
        )

        print("✓ Added pit lane")
    else:
        print("  ⚠ Pit lane JSON not found, skipping")

    print()

    # Update title
    fig.update_layout(
        title=f"Barber Motorsports Park - Filtered Brake Points (Zones Only)<br><sub>{len(in_zone):,} brake events in {len(brake_zones)} defined zones</sub>",
    )

    # Save HTML visualization
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(OUTPUT_HTML)
    print(f"✓ Saved visualization to: {OUTPUT_HTML}")
    print()

    print("=" * 80)
    print("✓ STEP 5c COMPLETE")
    print(f"✓ Open {OUTPUT_HTML} in browser to review filtered brake clusters")
    print("=" * 80)


if __name__ == "__main__":
    main()
