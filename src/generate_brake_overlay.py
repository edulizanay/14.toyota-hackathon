# ABOUTME: Generate brake point overlay visualization for Step 4
# ABOUTME: Overlays brake onset points on track outline for single driver/lap

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from brake_detection import detect_brake_peak_events
from track_rendering import generate_track_outline

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
OUTPUT_HTML = BASE_DIR / "data" / "visualizations" / "step4_brake_overlay.html"


def main():
    print("=" * 80)
    print("STEP 4: Brake Point Overlay")
    print("=" * 80)
    print()

    # Load telemetry
    print("Loading telemetry data...")
    df = pd.read_csv(TELEMETRY_PATH)
    print(f"✓ Loaded {len(df):,} rows")
    print()

    # Calculate P5 threshold (from Step 2 correction - using positive pressures only)
    print("Calculating brake pressure threshold (P5)...")
    all_pressures = pd.concat([df["pbrake_f"], df["pbrake_r"]])
    positive_pressures = all_pressures[all_pressures > 0]
    threshold = np.percentile(positive_pressures, 5)
    print(f"✓ P5 threshold: {threshold:.2f} bar")
    print()

    # Detect brake events for all drivers
    print("Detecting brake events (peaks)...")
    print("-" * 80)
    brake_events = detect_brake_peak_events(df, threshold)
    print()

    # Select one driver and one clean lap for visualization
    # Use car #13 (fastest driver)
    vehicle_number = 13
    vehicle_brakes = brake_events[brake_events["vehicle_number"] == vehicle_number]

    # Show lap statistics to help select a good lap
    lap_counts = vehicle_brakes.groupby("lap").size().sort_values(ascending=False)
    print(f"Vehicle #{vehicle_number} brake event counts by lap:")
    print(lap_counts.head(10))
    print()

    # Select a lap with 15-20 brake events (full lap, not pit entry)
    # Avoid laps with too many events (might include pit lane)
    good_laps = lap_counts[(lap_counts >= 15) & (lap_counts <= 20)]
    if len(good_laps) > 0:
        selected_lap = good_laps.index[0]  # Pick first good lap
    else:
        selected_lap = lap_counts.index[0]  # Fallback to most events

    lap_brake_count = lap_counts[selected_lap]

    print(f"Selected visualization: Vehicle #{vehicle_number}, Lap #{selected_lap}")
    print(f"Brake events in this lap: {lap_brake_count}")
    print()

    # Filter brake events for selected driver and lap
    lap_brakes = vehicle_brakes[vehicle_brakes["lap"] == selected_lap].copy()

    # Sort by timestamp to see event sequence
    lap_brakes = lap_brakes.sort_values("timestamp")

    # Show first few brake events for diagnostics
    print("First 5 brake events in selected lap:")
    print(
        lap_brakes[["timestamp", "x_meters", "y_meters", "brake_pressure"]]
        .head()
        .to_string(index=False)
    )
    print()

    # Generate track outline
    print("Generating track outline...")
    print("-" * 80)
    x_smooth, y_smooth, fig = generate_track_outline(
        df,
        vehicle_number=vehicle_number,
        lap_number=selected_lap,
        resample_step_m=2.0,
        spike_threshold_m=10.0,
        savgol_window=31,
        savgol_poly=3,
        wrap_count=25,
    )
    print()

    # Overlay brake points on track
    print("Overlaying brake points...")
    print("-" * 80)

    # Add brake onset points as scatter
    fig.add_trace(
        go.Scatter(
            x=lap_brakes["x_meters"],
            y=lap_brakes["y_meters"],
            mode="markers",
            marker=dict(
                size=10,
                color=lap_brakes["brake_pressure"],
                colorscale="Reds",
                showscale=True,
                colorbar=dict(
                    title="Brake Pressure (bar)",
                    x=1.02,
                    len=0.67,  # 2/3 of original size
                    y=0.335,  # Center it vertically
                ),
                line=dict(color="white", width=1),
            ),
            name="Brake Points",
            hovertemplate=(
                "Brake Onset<br>"
                "x: %{x:.1f}m<br>"
                "y: %{y:.1f}m<br>"
                "Pressure: %{marker.color:.1f} bar<br>"
                "Timestamp: %{customdata}<br>"
                "<extra></extra>"
            ),
            customdata=lap_brakes["timestamp"],
        )
    )

    # Update title
    fig.update_layout(
        title=f"Barber Motorsports Park - Brake Point Analysis<br><sub>Vehicle #{vehicle_number}, Lap #{selected_lap} ({lap_brake_count} brake events)</sub>",
    )

    print(f"✓ Added {len(lap_brakes)} brake peak points")
    print(
        f"  Brake pressure range: {lap_brakes['brake_pressure'].min():.1f} - {lap_brakes['brake_pressure'].max():.1f} bar"
    )
    print(f"  Front brake led: {(lap_brakes['brake_type'] == 'front').sum()} events")
    print(f"  Rear brake led: {(lap_brakes['brake_type'] == 'rear').sum()} events")
    print()

    # Save HTML visualization
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(OUTPUT_HTML)
    print(f"✓ Saved visualization to: {OUTPUT_HTML}")
    print()

    print("=" * 80)
    print("✓ BRAKE OVERLAY COMPLETE")
    print(f"✓ Open {OUTPUT_HTML} in browser to review")
    print("=" * 80)


if __name__ == "__main__":
    main()
