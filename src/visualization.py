# ABOUTME: Interactive visualization utilities for brake point analysis
# ABOUTME: Creates reference driver view and comparison dashboards

import json
import plotly.graph_objects as go
from pathlib import Path
from track_rendering import generate_track_outline

BASE_DIR = Path(__file__).parent.parent
BRAKE_EVENTS_CSV = BASE_DIR / "data" / "brake-analysis" / "brake_events.csv"
CORNER_DEFINITIONS_JSON = BASE_DIR / "data" / "brake-analysis" / "corner_definitions.json"
PIT_LANE_JSON = BASE_DIR / "data" / "gps-tracks" / "pit_lane.json"


def plot_reference_driver(
    telemetry_df,
    brake_events_df,
    reference_vehicle_number,
    output_path,
):
    """
    Create reference driver visualization with gray brake point clusters.

    Args:
        telemetry_df: Full telemetry DataFrame for track rendering
        brake_events_df: Brake events DataFrame
        reference_vehicle_number: Vehicle number of reference driver
        output_path: Path to save HTML file
    """
    print(f"Creating reference visualization for driver #{reference_vehicle_number}...")
    print()

    # Generate track outline
    print("Generating track outline...")
    print("-" * 80)
    x_smooth, y_smooth, fig = generate_track_outline(
        telemetry_df,
        vehicle_number=13,
        lap_number=None,
        resample_step_m=2.0,
        spike_threshold_m=10.0,
        savgol_window=31,
        savgol_poly=3,
        wrap_count=25,
    )
    print()

    # Filter brake events for reference driver (only in-zone events)
    ref_brakes = brake_events_df[
        (brake_events_df["vehicle_number"] == reference_vehicle_number)
        & (brake_events_df["zone_id"].notna())
    ].copy()

    print(f"Reference driver brake points: {len(ref_brakes)}")
    print()

    # Load zone definitions
    with open(CORNER_DEFINITIONS_JSON, "r") as f:
        zones = json.load(f)

    # Define colors for zones
    zone_colors = {
        1: "#FF6B6B",  # Red
        2: "#4ECDC4",  # Teal
        3: "#45B7D1",  # Light blue
        4: "#96CEB4",  # Sage green
        5: "#FFEAA7",  # Yellow
        6: "#DDA15E",  # Orange
        7: "#C77DFF",  # Purple
        8: "#06FFA5",  # Mint
    }

    # Plot brake points by zone (semi-transparent gray with zone color outline)
    print("Adding reference brake points by zone...")
    for zone_id in sorted(ref_brakes["zone_id"].dropna().unique()):
        zone_data = ref_brakes[ref_brakes["zone_id"] == zone_id]
        zone_info = next(z for z in zones if z["zone_id"] == int(zone_id))
        zone_color = zone_colors[int(zone_id)]

        fig.add_trace(
            go.Scatter(
                x=zone_data["x_meters"],
                y=zone_data["y_meters"],
                mode="markers",
                marker=dict(
                    size=6,
                    color="rgba(128, 128, 128, 0.4)",  # Semi-transparent gray
                    line=dict(color=zone_color, width=1.5),
                ),
                name=f"Zone {int(zone_id)}",
                hovertemplate=(
                    f"Zone {int(zone_id)}<br>"
                    + "x: %{x:.1f}m<br>y: %{y:.1f}m<br>"
                    + "<extra></extra>"
                ),
            )
        )

    print(f"✓ Added {len(ref_brakes)} reference brake points")
    print()

    # Calculate and display zone centroids with badges
    print("Adding zone badges at centroids...")
    for zone_id in sorted(ref_brakes["zone_id"].dropna().unique()):
        zone_data = ref_brakes[ref_brakes["zone_id"] == zone_id]

        # Calculate centroid
        centroid_x = zone_data["x_meters"].mean()
        centroid_y = zone_data["y_meters"].mean()

        zone_color = zone_colors[int(zone_id)]

        # Add badge
        fig.add_trace(
            go.Scatter(
                x=[centroid_x],
                y=[centroid_y],
                mode="markers+text",
                marker=dict(
                    size=28,
                    color="rgba(255, 255, 255, 0.9)",
                    line=dict(color=zone_color, width=3),
                ),
                text=f"Z{int(zone_id)}",
                textposition="middle center",
                textfont=dict(size=11, color="black", family="Arial Black"),
                name=f"Zone {int(zone_id)} Center",
                showlegend=False,
                hovertemplate=(
                    f"Zone {int(zone_id)} Centroid<br>"
                    + "x: %{x:.1f}m<br>y: %{y:.1f}m<br>"
                    + f"Brake points: {len(zone_data)}<br>"
                    + "<extra></extra>"
                ),
            )
        )

    print(f"✓ Added {len(ref_brakes['zone_id'].dropna().unique())} zone badges")
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
                showlegend=False,
                hoverinfo="skip",
            )
        )

        print("✓ Added pit lane")
    print()

    # Update layout
    fig.update_layout(
        title=f"Barber Motorsports Park - Reference Driver #{reference_vehicle_number}<br><sub>Fastest driver brake point clusters (gray) with zone badges</sub>",
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(20, 20, 20, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.3)",
            borderwidth=1,
        ),
    )

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"✓ Saved reference visualization to: {output_path}")
    print()

    return fig
