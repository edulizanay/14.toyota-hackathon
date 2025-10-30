# ABOUTME: Generate histogram visualization of brake point density along track distance
# ABOUTME: Used to manually identify brake zone boundaries for zone definition JSON

import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from brake_detection import detect_brake_events

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
CORNER_LABELS_JSON = BASE_DIR / "data" / "gps-tracks" / "corner_labels.json"
OUTPUT_HTML = BASE_DIR / "temp" / "brake_histogram.html"


def project_to_centerline(brake_x, brake_y, centerline_x, centerline_y):
    """
    Project brake points onto track centerline and return track distances.

    Returns:
        track_distances: array of distances along centerline (0 to lap_length)
    """
    # Calculate cumulative distance along centerline
    dx = np.diff(centerline_x)
    dy = np.diff(centerline_y)
    segment_lengths = np.sqrt(dx**2 + dy**2)
    cumulative_distance = np.concatenate([[0], np.cumsum(segment_lengths)])

    # For each brake point, find nearest centerline point
    track_distances = []

    for bx, by in zip(brake_x, brake_y):
        # Calculate distance to all centerline points
        distances = np.sqrt((centerline_x - bx) ** 2 + (centerline_y - by) ** 2)
        nearest_idx = np.argmin(distances)

        # Use the cumulative distance at that point
        track_distances.append(cumulative_distance[nearest_idx])

    return np.array(track_distances)


def main():
    print("=" * 80)
    print("Brake Density Histogram - Manual Zone Definition Tool")
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

    # Extract track centerline from fastest driver (vehicle #13)
    print("Extracting track centerline...")
    vehicle_13 = df[df["vehicle_number"] == 13].copy()

    # Get a clean lap (lap 18 was used in previous steps)
    lap_data = vehicle_13[vehicle_13["lap"] == 18].sort_values("timestamp")

    if len(lap_data) == 0:
        print("ERROR: No data for vehicle #13, lap 18")
        return

    centerline_x = lap_data["x_meters"].values
    centerline_y = lap_data["y_meters"].values

    # Calculate total track length
    dx = np.diff(centerline_x)
    dy = np.diff(centerline_y)
    track_length = np.sum(np.sqrt(dx**2 + dy**2))
    print(f"✓ Track length: {track_length:.1f}m ({len(centerline_x)} points)")
    print()

    # Project brake points onto centerline
    print("Projecting brake points to centerline...")
    brake_track_distances = project_to_centerline(
        brake_events_filtered["x_meters"].values,
        brake_events_filtered["y_meters"].values,
        centerline_x,
        centerline_y,
    )
    print(f"✓ Projected {len(brake_track_distances):,} brake points")
    print()

    # Create histogram
    print("Creating histogram...")
    bin_size = 10  # meters
    bins = np.arange(0, track_length + bin_size, bin_size)
    counts, bin_edges = np.histogram(brake_track_distances, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    print(f"✓ Histogram: {len(bins) - 1} bins of {bin_size}m each")
    print(f"✓ Max brake density: {counts.max()} events in one bin")
    print()

    # Create figure
    fig = go.Figure()

    # Add histogram
    fig.add_trace(
        go.Bar(
            x=bin_centers,
            y=counts,
            width=bin_size * 0.9,
            marker=dict(color="rgba(255, 100, 100, 0.7)", line=dict(width=0)),
            name="Brake Event Density",
            hovertemplate="Distance: %{x:.0f}m<br>Brake events: %{y}<extra></extra>",
        )
    )

    # Load and overlay corner positions
    print("Loading corner labels...")
    if CORNER_LABELS_JSON.exists():
        with open(CORNER_LABELS_JSON, "r") as f:
            corner_labels = json.load(f)

        # Project corner positions onto centerline
        corner_x = [c["x_meters"] for c in corner_labels]
        corner_y = [c["y_meters"] for c in corner_labels]
        corner_numbers = [c["corner_number"] for c in corner_labels]

        corner_track_distances = project_to_centerline(
            corner_x, corner_y, centerline_x, centerline_y
        )

        # Add vertical lines for corner positions
        max_count = counts.max()
        for dist, num in zip(corner_track_distances, corner_numbers):
            fig.add_trace(
                go.Scatter(
                    x=[dist, dist],
                    y=[0, max_count * 1.1],
                    mode="lines",
                    line=dict(color="rgba(100, 100, 255, 0.4)", width=1, dash="dash"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

            # Add corner number annotation
            fig.add_annotation(
                x=dist,
                y=max_count * 1.15,
                text=f"C{num}",
                showarrow=False,
                font=dict(size=10, color="rgba(100, 100, 255, 0.8)"),
            )

        print(f"✓ Added {len(corner_labels)} corner markers")
    else:
        print("  ⚠ Corner labels JSON not found, skipping")

    print()

    # Update layout
    fig.update_layout(
        title="Brake Event Density Along Track<br><sub>Use this to identify brake zone start/end distances for manual definition</sub>",
        xaxis=dict(
            title="Distance Along Track (meters)",
            range=[0, track_length],
            gridcolor="rgba(128, 128, 128, 0.2)",
        ),
        yaxis=dict(
            title="Brake Event Count (per 10m bin)",
            gridcolor="rgba(128, 128, 128, 0.2)",
        ),
        template="plotly_white",
        hovermode="x unified",
        height=600,
        showlegend=True,
    )

    # Save HTML visualization
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(OUTPUT_HTML)
    print(f"✓ Saved histogram to: {OUTPUT_HTML}")
    print()

    print("=" * 80)
    print("NEXT STEPS:")
    print("1. Open the histogram in your browser")
    print("2. Identify brake zone clusters (peaks in the histogram)")
    print("3. Note the start/end distances for each significant brake zone")
    print("4. Create data/track-layout/brake_zones.json with zone definitions")
    print("=" * 80)


if __name__ == "__main__":
    main()
