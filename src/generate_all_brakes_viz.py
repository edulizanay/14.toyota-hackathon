# ABOUTME: Generate visualization of ALL brake points from ALL drivers (Step 5a)
# ABOUTME: Used to identify brake clusters and define corner zones

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
CORNER_LABELS_JSON = BASE_DIR / "data" / "gps-tracks" / "corner_labels.json"
PIT_LANE_JSON = BASE_DIR / "data" / "gps-tracks" / "pit_lane.json"
OUTPUT_HTML = BASE_DIR / "data" / "visualizations" / "step5a_all_brakes.html"


def main():
    print("=" * 80)
    print("STEP 5a: Plot All Brake Points (All Drivers)")
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

    # Detect brake events for all drivers
    print("Detecting brake events for all drivers...")
    print("-" * 80)
    brake_events = detect_brake_events(df, threshold)
    print()

    # Filter to racing laps only (distance 3500-4000m to exclude pit laps)
    print("Filtering to racing laps only...")
    racing_brake_events = []

    for (vehicle, lap), group in brake_events.groupby(["vehicle_number", "lap"]):
        lap_telemetry = df[(df["vehicle_number"] == vehicle) & (df["lap"] == lap)]

        if len(lap_telemetry) > 0:
            # Calculate lap distance
            lap_telemetry_sorted = lap_telemetry.sort_values("timestamp")
            dx = np.diff(lap_telemetry_sorted["x_meters"].values)
            dy = np.diff(lap_telemetry_sorted["y_meters"].values)
            lap_distance = np.sum(np.sqrt(dx**2 + dy**2))

            # Keep only full racing laps
            if 3500 <= lap_distance <= 4000:
                racing_brake_events.append(group)

    brake_events_filtered = pd.concat(racing_brake_events, ignore_index=True)

    print(f"✓ Total brake events (all laps): {len(brake_events):,}")
    print(f"✓ Racing lap brake events: {len(brake_events_filtered):,}")
    print()

    # Generate track outline (use fastest driver for reference)
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

    # Overlay ALL brake points as semi-transparent scatter
    print("Overlaying all brake points...")
    print("-" * 80)

    fig.add_trace(
        go.Scatter(
            x=brake_events_filtered["x_meters"],
            y=brake_events_filtered["y_meters"],
            mode="markers",
            marker=dict(
                size=4,
                color="rgba(255, 100, 100, 0.3)",  # Semi-transparent red
                line=dict(color="rgba(255, 255, 255, 0.2)", width=0.5),
            ),
            name="All Brake Points",
            hovertemplate=(
                "Brake Point<br>x: %{x:.1f}m<br>y: %{y:.1f}m<br><extra></extra>"
            ),
        )
    )

    print(f"✓ Added {len(brake_events_filtered):,} brake points")
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

        print(f"✓ Added pit lane ({len(centerline)} points)")
    else:
        print("  ⚠ Pit lane JSON not found, skipping")

    print()

    # Load and overlay corner labels
    print("Loading corner labels...")
    if CORNER_LABELS_JSON.exists():
        with open(CORNER_LABELS_JSON, "r") as f:
            corner_labels = json.load(f)

        corner_x = [c["x_meters"] for c in corner_labels]
        corner_y = [c["y_meters"] for c in corner_labels]
        corner_text = [c["label"] for c in corner_labels]

        fig.add_trace(
            go.Scatter(
                x=corner_x,
                y=corner_y,
                mode="markers+text",
                marker=dict(
                    size=24,  # Increased from 12 to 24
                    color="rgba(255, 255, 255, 0.95)",
                    line=dict(color="rgba(0, 0, 0, 0.9)", width=2),
                ),
                text=corner_text,
                textposition="middle center",
                textfont=dict(size=12, color="black", family="Arial Black"),
                name="Corner Numbers",
                hovertemplate="Corner %{text}<br>x: %{x:.1f}m<br>y: %{y:.1f}m<extra></extra>",
            )
        )

        print(f"✓ Added {len(corner_labels)} corner labels")
    else:
        print("  ⚠ Corner labels JSON not found, skipping")

    print()

    # Update title
    fig.update_layout(
        title=f"Barber Motorsports Park - All Brake Points<br><sub>{len(brake_events_filtered):,} brake events from racing laps (all drivers)</sub>",
    )

    # Save HTML visualization
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(OUTPUT_HTML)
    print(f"✓ Saved visualization to: {OUTPUT_HTML}")
    print()

    print("=" * 80)
    print("✓ STEP 5a COMPLETE")
    print(f"✓ Open {OUTPUT_HTML} in browser to review corner numbers and pit lane")
    print("=" * 80)


if __name__ == "__main__":
    main()
