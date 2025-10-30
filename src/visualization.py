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

    # Plot brake points by zone (fully gray - fill and outline)
    print("Adding reference brake points by zone...")
    for zone_id in sorted(ref_brakes["zone_id"].dropna().unique()):
        zone_data = ref_brakes[ref_brakes["zone_id"] == zone_id]
        zone_info = next(z for z in zones if z["zone_id"] == int(zone_id))

        fig.add_trace(
            go.Scatter(
                x=zone_data["x_meters"],
                y=zone_data["y_meters"],
                mode="markers",
                marker=dict(
                    size=6,
                    color="rgba(128, 128, 128, 0.4)",  # Semi-transparent gray
                    line=dict(color="rgba(128, 128, 128, 0.6)", width=1.5),  # Gray outline
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


def create_interactive_dashboard(
    telemetry_df,
    brake_events_df,
    driver_summary_df,
    reference_vehicle_number,
    output_path,
):
    """
    Create interactive dashboard with driver selection dropdown.

    Args:
        telemetry_df: Full telemetry DataFrame for track rendering
        brake_events_df: Brake events DataFrame
        driver_summary_df: Driver summary with lap times
        reference_vehicle_number: Vehicle number of reference driver
        output_path: Path to save HTML file
    """
    print(f"Creating interactive dashboard with reference driver #{reference_vehicle_number}...")
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

    # Get list of all drivers with lap times
    valid_drivers = driver_summary_df.dropna(subset=["fastest_lap_seconds"]).sort_values("fastest_lap_seconds")
    driver_list = valid_drivers["vehicle_number"].astype(int).tolist()

    print(f"Available drivers for comparison: {len(driver_list)}")
    print()

    # Add reference driver (gray)
    print("Adding reference driver brake points...")
    ref_brakes = brake_events_df[
        (brake_events_df["vehicle_number"] == reference_vehicle_number)
        & (brake_events_df["zone_id"].notna())
    ].copy()

    for zone_id in sorted(ref_brakes["zone_id"].dropna().unique()):
        zone_data = ref_brakes[ref_brakes["zone_id"] == zone_id]

        fig.add_trace(
            go.Scatter(
                x=zone_data["x_meters"],
                y=zone_data["y_meters"],
                mode="markers",
                marker=dict(
                    size=6,
                    color="rgba(128, 128, 128, 0.4)",
                    line=dict(color="rgba(128, 128, 128, 0.6)", width=1.5),
                ),
                name=f"Reference Z{int(zone_id)}",
                visible=True,
                hovertemplate=(
                    f"Reference - Zone {int(zone_id)}<br>"
                    + "x: %{x:.1f}m<br>y: %{y:.1f}m<br>"
                    + "<extra></extra>"
                ),
            )
        )

    print(f"✓ Added {len(ref_brakes)} reference brake points")
    print()

    # Add zone badges
    print("Adding zone badges...")
    for zone_id in sorted(ref_brakes["zone_id"].dropna().unique()):
        zone_data = ref_brakes[ref_brakes["zone_id"] == zone_id]
        centroid_x = zone_data["x_meters"].mean()
        centroid_y = zone_data["y_meters"].mean()
        zone_color = zone_colors[int(zone_id)]

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
                name=f"Zone {int(zone_id)}",
                visible=True,
                showlegend=False,
                hoverinfo="skip",
            )
        )

    print("✓ Added zone badges")
    print()

    # Add pit lane
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
                visible=True,
                showlegend=False,
                hoverinfo="skip",
            )
        )
        print("✓ Added pit lane")
    print()

    # Prepare traces for all drivers (one set of 8 traces per driver)
    print("Preparing comparison driver traces...")
    driver_traces_start_idx = len(fig.data)  # Track where driver traces start

    for driver_num in driver_list:
        driver_brakes = brake_events_df[
            (brake_events_df["vehicle_number"] == driver_num)
            & (brake_events_df["zone_id"].notna())
        ].copy()

        for zone_id in range(1, 9):  # All 8 zones
            zone_data = driver_brakes[driver_brakes["zone_id"] == zone_id]
            zone_color = zone_colors[zone_id]

            # Initially hide all comparison drivers (only reference visible by default)
            is_visible = False

            if len(zone_data) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=zone_data["x_meters"],
                        y=zone_data["y_meters"],
                        mode="markers",
                        marker=dict(
                            size=7,
                            color=zone_color,
                            opacity=0.7,
                            line=dict(color="rgba(255, 255, 255, 0.5)", width=1),
                        ),
                        name=f"Driver {driver_num} Z{zone_id}",
                        visible=is_visible,
                        hovertemplate=(
                            f"Driver #{driver_num} - Zone {zone_id}<br>"
                            + "x: %{x:.1f}m<br>y: %{y:.1f}m<br>"
                            + "<extra></extra>"
                        ),
                    )
                )
            else:
                # Add empty trace as placeholder
                fig.add_trace(
                    go.Scatter(
                        x=[],
                        y=[],
                        mode="markers",
                        name=f"Driver {driver_num} Z{zone_id}",
                        visible=is_visible,
                    )
                )

    print(f"✓ Added traces for {len(driver_list)} drivers")
    print()

    # Create dropdown buttons
    print("Creating dropdown menu...")
    buttons = []

    # "None" button - show only reference
    none_visible = [True] * driver_traces_start_idx + [False] * (len(driver_list) * 8)
    buttons.append(
        dict(
            label="None (Reference Only)",
            method="update",
            args=[
                {"visible": none_visible},
                {"title": f"Barber Motorsports Park - Reference Driver #{reference_vehicle_number}"},
            ],
        )
    )

    # One button per driver
    for i, driver_num in enumerate(driver_list):
        driver_info = valid_drivers[valid_drivers["vehicle_number"] == driver_num].iloc[0]
        lap_time = driver_info["fastest_lap_time"]

        # Calculate visibility: reference + this driver's 8 traces
        visible = [True] * driver_traces_start_idx + [False] * (len(driver_list) * 8)
        start_idx = driver_traces_start_idx + (i * 8)
        end_idx = start_idx + 8
        for j in range(start_idx, end_idx):
            visible[j] = True

        buttons.append(
            dict(
                label=f"Driver #{driver_num} ({lap_time})",
                method="update",
                args=[
                    {"visible": visible},
                    {"title": f"Barber Motorsports Park - Driver #{driver_num} vs Reference #{reference_vehicle_number}<br><sub>Driver #{driver_num} lap time: {lap_time}</sub>"},
                ],
            )
        )

    print(f"✓ Created {len(buttons)} dropdown options")
    print()

    # Update layout with dropdown
    fig.update_layout(
        title=f"Barber Motorsports Park - Reference Driver #{reference_vehicle_number}<br><sub>Select a driver from the dropdown to compare</sub>",
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.02,
                xanchor="left",
                y=0.98,
                yanchor="top",
                bgcolor="rgba(20, 20, 20, 0.9)",
                bordercolor="rgba(255, 255, 255, 0.3)",
                borderwidth=2,
                font=dict(size=11, color="white"),
            )
        ],
        legend=dict(
            x=0.02,
            y=0.88,
            bgcolor="rgba(20, 20, 20, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.3)",
            borderwidth=1,
        ),
    )

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"✓ Saved interactive dashboard to: {output_path}")
    print()

    return fig
