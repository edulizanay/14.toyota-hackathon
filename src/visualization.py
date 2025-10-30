# ABOUTME: Interactive visualization utilities for brake point analysis
# ABOUTME: Creates reference driver view and comparison dashboards

import json
import math
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from track_rendering import generate_track_outline


def rotate_coordinates(x, y, angle_degrees):
    """
    Rotate 2D coordinates counterclockwise by angle_degrees.

    Args:
        x: x-coordinates (array-like)
        y: y-coordinates (array-like)
        angle_degrees: rotation angle in degrees (positive = counterclockwise)

    Returns:
        x_rot, y_rot: rotated coordinates
    """
    angle_rad = math.radians(angle_degrees)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    x = np.asarray(x)
    y = np.asarray(y)

    x_rot = x * cos_a - y * sin_a
    y_rot = x * sin_a + y * cos_a

    return x_rot, y_rot

BASE_DIR = Path(__file__).parent.parent
BRAKE_EVENTS_CSV = BASE_DIR / "data" / "brake-analysis" / "brake_events.csv"
CORNER_DEFINITIONS_JSON = BASE_DIR / "data" / "brake-analysis" / "corner_definitions.json"
PIT_LANE_JSON = BASE_DIR / "data" / "gps-tracks" / "pit_lane.json"
CORNER_LABELS_JSON = BASE_DIR / "data" / "gps-tracks" / "corner_labels.json"


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

    # Prepare corner label overlay as rounded badges (circle shapes + centered text)
    # Default is OFF; expose a single toggle button
    corner_text_ann = []
    corner_shapes = []
    base_annotations = []
    base_shapes = []

    try:
        if getattr(fig.layout, "annotations", None):
            base_annotations = list(fig.layout.annotations)
    except Exception:
        base_annotations = []
    try:
        if getattr(fig.layout, "shapes", None):
            base_shapes = list(fig.layout.shapes)
    except Exception:
        base_shapes = []

    if CORNER_LABELS_JSON.exists():
        with open(CORNER_LABELS_JSON, "r") as f:
            corner_labels = json.load(f)

        # Radius for circle badges in meters (approx track-relative size)
        # Halved from 12.0 → 6.0 to reduce badge size
        RADIUS_M = 6.0

        for c in corner_labels:
            label_text = str(c.get("label", c.get("corner_number", "")))
            x0 = c["x_meters"] - RADIUS_M
            x1 = c["x_meters"] + RADIUS_M
            y0 = c["y_meters"] - RADIUS_M
            y1 = c["y_meters"] + RADIUS_M

            # Circle behind the label (rounded look)
            corner_shapes.append(
                dict(
                    type="circle",
                    xref="x",
                    yref="y",
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    line=dict(color="rgba(0, 0, 0, 0.9)", width=2),
                    fillcolor="rgba(255, 255, 255, 0.95)",
                    layer="above",
                )
            )

            # Text centered on circle (no box/border)
            corner_text_ann.append(
                dict(
                    x=c["x_meters"],
                    y=c["y_meters"],
                    xref="x",
                    yref="y",
                    text=label_text,
                    showarrow=False,
                    align="center",
                    # Font reduced to half of the previous large setting (48 → 24)
                    font=dict(size=24, color="black", family="Arial Black"),
                    bgcolor="rgba(0,0,0,0)",
                )
            )
        print(f"✓ Prepared {len(corner_text_ann)} rounded corner labels (toggleable)")
    else:
        print("  ⚠ Corner labels JSON not found, skipping corner overlay toggle")
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

    # Build a single-button toggle for corner labels using args/args2
    toggle_menu = None
    if len(corner_text_ann) > 0:
        toggle_menu = dict(
            type="buttons",
            direction="right",
            x=0.02,
            xanchor="left",
            y=0.92,
            yanchor="top",
            # Light background + dark text to avoid white-on-white when active
            bgcolor="rgba(235, 235, 235, 0.95)",
            bordercolor="rgba(60, 60, 60, 0.8)",
            borderwidth=2,
            pad={"r": 10, "t": 6},
            font=dict(size=12, color="#111111"),
            buttons=[
                dict(
                    label="Corners",
                    method="relayout",
                    args=[
                        {
                            "annotations": base_annotations + corner_text_ann,
                            "shapes": base_shapes + corner_shapes,
                        }
                    ],
                    args2=[
                        {
                            "annotations": base_annotations,
                            "shapes": base_shapes,
                        }
                    ],
                )
            ],
        )

    # Update layout with dropdown and (optional) corner toggle buttons
    updatemenus = [
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
    ]
    if toggle_menu:
        updatemenus.append(toggle_menu)

    fig.update_layout(
        title=f"Barber Motorsports Park - Reference Driver #{reference_vehicle_number}<br><sub>Select a driver from the dropdown to compare</sub>",
        updatemenus=updatemenus,
        legend=dict(
            x=0.02,
            y=0.86,  # nudge legend down slightly to avoid overlap with toggle buttons
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


def create_zone_focused_dashboard(
    telemetry_df,
    brake_events_df,
    driver_summary_df,
    reference_vehicle_number,
    output_path,
):
    """
    Create zone-focused interactive dashboard with zone pills and driver chips.

    Shows one zone at a time via horizontal zone pills.
    Uses axis range cropping (relayout) instead of trace visibility per zone.
    Reference points in white, comparison driver in per-point zone colors.

    Args:
        telemetry_df: Full telemetry DataFrame for track rendering
        brake_events_df: Brake events DataFrame
        driver_summary_df: Driver summary with lap times
        reference_vehicle_number: Vehicle number of reference driver
        output_path: Path to save HTML file
    """
    from corner_detection import calculate_zone_boundaries

    print(f"Creating zone-focused dashboard (reference #{reference_vehicle_number})...")
    print()

    # 1) Track outline
    print("Generating track outline...")
    print("-" * 80)
    _, _, fig = generate_track_outline(
        telemetry_df,
        vehicle_number=reference_vehicle_number,
        lap_number=None,
        resample_step_m=2.0,
        spike_threshold_m=10.0,
        savgol_window=31,
        savgol_poly=3,
        wrap_count=25,
    )
    print()

    # Rotate track outline for better viewing angle
    rotation_angle = -45.0  # Negative = clockwise
    print(f"Rotating visualization by {abs(rotation_angle)}° clockwise...")
    for trace in fig.data:
        if trace.x is not None and trace.y is not None:
            x_rot, y_rot = rotate_coordinates(trace.x, trace.y, rotation_angle)
            trace.x = x_rot
            trace.y = y_rot
    print("✓ Rotated track outline")
    print()

    # Rotate brake event coordinates
    brake_events_df = brake_events_df.copy()
    x_rot, y_rot = rotate_coordinates(
        brake_events_df["x_meters"].values,
        brake_events_df["y_meters"].values,
        rotation_angle
    )
    brake_events_df["x_meters"] = x_rot
    brake_events_df["y_meters"] = y_rot
    print("✓ Rotated brake event coordinates")
    print()

    # 2) Zone colors
    zone_colors = {
        1: "#FF6B6B", 2: "#4ECDC4", 3: "#45B7D1", 4: "#96CEB4",
        5: "#FFEAA7", 6: "#DDA15E", 7: "#C77DFF", 8: "#06FFA5",
    }

    # 3) Compute zone bboxes
    print("Computing zone boundaries...")
    zone_bounds = calculate_zone_boundaries(brake_events_df, padding_m=20.0)
    zone_order = sorted(zone_bounds.keys())
    print(f"✓ Calculated boundaries for {len(zone_order)} zones")
    print()

    # 4) Zone badges
    print("Adding zone badges...")
    ref_brakes = brake_events_df[
        (brake_events_df["vehicle_number"] == reference_vehicle_number)
        & (brake_events_df["zone_id"].notna())
    ].copy()

    for zid in sorted(ref_brakes["zone_id"].dropna().unique()):
        dfz = ref_brakes[ref_brakes["zone_id"] == zid]
        cx, cy = dfz["x_meters"].mean(), dfz["y_meters"].mean()
        fig.add_trace(go.Scatter(
            x=[cx], y=[cy],
            mode="markers+text",
            marker=dict(size=28, color="rgba(255,255,255,0.9)", line=dict(color=zone_colors[int(zid)], width=3)),
            text=f"Z{int(zid)}", textposition="middle center",
            textfont=dict(size=11, color="black", family="Arial Black"),
            name=f"Zone {int(zid)}", showlegend=False, hoverinfo="skip",
            visible=False,  # Hidden by default
        ))
    print(f"✓ Added {len(ref_brakes['zone_id'].dropna().unique())} zone badges")
    print()

    # 5) Corner labels (1-17)
    print("Loading corner labels...")
    if CORNER_LABELS_JSON.exists():
        corner_labels = json.loads(CORNER_LABELS_JSON.read_text())
        corner_x = [c["x_meters"] for c in corner_labels]
        corner_y = [c["y_meters"] for c in corner_labels]
        corner_text = [c["label"] for c in corner_labels]

        # Rotate corner labels
        corner_x_rot, corner_y_rot = rotate_coordinates(corner_x, corner_y, rotation_angle)

        fig.add_trace(go.Scatter(
            x=corner_x_rot, y=corner_y_rot,
            mode="markers+text",
            marker=dict(size=24, color="rgba(255,255,255,0.15)", line=dict(color="rgba(255,165,0,0.8)", width=2)),
            text=corner_text, textposition="middle center",
            textfont=dict(size=10, color="orange", family="Arial Black"),
            name="Track Corners",
            showlegend=False,
            hovertemplate="Corner %{text}<extra></extra>",
            visible=True,
        ))
        print(f"✓ Added {len(corner_labels)} corner labels")
    else:
        print("⚠ Corner labels file not found, skipping")
    print()

    # 6) Reference trace (white, all zones)
    print("Adding reference driver brake points...")
    fig.add_trace(go.Scatter(
        x=ref_brakes["x_meters"], y=ref_brakes["y_meters"],
        mode="markers",
        marker=dict(size=8, color="rgba(255,255,255,0.6)"),
        name=f"Winner (#{reference_vehicle_number})",
        hovertemplate="Ref x: %{x:.1f}m<br>y: %{y:.1f}m<extra></extra>",
        visible=True,
    ))
    print(f"✓ Added {len(ref_brakes)} reference brake points (white)")
    print()

    # 7) One comparison trace per driver (all zones), colored by zone_id
    print("Preparing comparison driver traces...")
    valid = driver_summary_df.dropna(subset=["fastest_lap_seconds"]).sort_values("fastest_lap_seconds")
    driver_list = [int(v) for v in valid["vehicle_number"].tolist() if int(v) != reference_vehicle_number]

    def color_for_zone(series):
        return [zone_colors.get(int(z), "#999") for z in series.fillna(0).astype(int)]

    for drv in driver_list:
        df_drv = brake_events_df[
            (brake_events_df["vehicle_number"] == drv) & (brake_events_df["zone_id"].notna())
        ].copy()
        colors = color_for_zone(df_drv["zone_id"])
        fig.add_trace(go.Scatter(
            x=df_drv["x_meters"], y=df_drv["y_meters"],
            mode="markers",
            marker=dict(size=10, color=colors, line=dict(color="rgba(255,255,255,0.7)", width=2)),
            name=f"#{drv} ({valid[valid['vehicle_number'] == drv].iloc[0]['fastest_lap_time']})",
            hovertemplate=f"#{drv} x: %{{x:.1f}}m<br>y: %{{y:.1f}}m<extra></extra>",
            visible="legendonly",  # hidden by default, but toggleable via legend
            showlegend=True,
        ))
    print(f"✓ Added traces for {len(driver_list)} drivers")
    print()

    # 8) Zone pills (relayout only)
    print("Creating zone selector pills...")

    # Calculate full track bounds from all brake events
    all_brake_x = brake_events_df["x_meters"].dropna()
    all_brake_y = brake_events_df["y_meters"].dropna()
    full_x_min, full_x_max = all_brake_x.min(), all_brake_x.max()
    full_y_min, full_y_max = all_brake_y.min(), all_brake_y.max()

    # Add 15% padding to full view (proportional to track dimensions)
    track_width = full_x_max - full_x_min
    track_height = full_y_max - full_y_min
    x_padding = 0.15 * track_width
    y_padding = 0.15 * track_height
    full_x_min -= x_padding
    full_x_max += x_padding
    full_y_min -= y_padding
    full_y_max += y_padding

    zone_buttons = []

    # Add "Full" button first (default view)
    zone_buttons.append(dict(
        label="Full",
        method="relayout",
        args=[{
            "xaxis.range": [full_x_min, full_x_max],
            "yaxis.range": [full_y_min, full_y_max],
        }],
    ))

    # Add zone-specific buttons
    for zid in sorted(zone_bounds.keys()):
        zb = zone_bounds[zid]
        zone_buttons.append(dict(
            label=f"Z{zid}",
            method="relayout",
            args=[{
                "xaxis.range": [zb["x_min"], zb["x_max"]],
                "yaxis.range": [zb["y_min"], zb["y_max"]],
            }],
        ))
    print(f"✓ Created {len(zone_buttons)} zone pill buttons (Full + {len(zone_bounds)} zones)")
    print()

    # 9) Corner labels and zone badges toggle buttons
    print("Creating toggle buttons for labels...")
    # Find trace indices
    # Traces: track surface (0) + centerline (1) + zone badges (2-9) + corner labels (10) + ref (11) + drivers (12+)
    base_trace_count = len(fig.data) - len(driver_list)  # Everything except driver traces
    zone_badges_indices = list(range(2, 10))  # Zone badges are traces 2-9 (8 zones)
    corner_labels_idx = base_trace_count - 2  # Corner labels is 2 traces before drivers (ref is -1)

    zone_badges_toggle_button = dict(
        type="buttons",
        direction="right",
        buttons=[dict(
            label="Zone Badges",
            method="restyle",
            args=[{"visible": True}, zone_badges_indices],
            args2=[{"visible": False}, zone_badges_indices],
        )],
        x=0.98, xanchor="right", y=0.07, yanchor="bottom",  # Bottom right, below legend
        showactive=False,
        bgcolor="rgba(26,26,26,0.95)", bordercolor="rgba(100,200,255,0.4)", borderwidth=1,
        pad=dict(r=4, l=4, t=4, b=4), font=dict(size=11, color="rgba(100,200,255,0.9)"),
    )

    corner_toggle_button = dict(
        type="buttons",
        direction="right",
        buttons=[dict(
            label="Corner Labels",
            method="restyle",
            args=[{"visible": True}, [corner_labels_idx]],
            args2=[{"visible": False}, [corner_labels_idx]],
        )],
        x=0.98, xanchor="right", y=0.13, yanchor="bottom",  # Bottom right, above zone badges
        showactive=False,
        bgcolor="rgba(26,26,26,0.95)", bordercolor="rgba(255,165,0,0.4)", borderwidth=1,
        pad=dict(r=4, l=4, t=4, b=4), font=dict(size=11, color="orange"),
    )

    axes_toggle_button = dict(
        type="buttons",
        direction="right",
        buttons=[dict(
            label="Axes",
            method="relayout",
            args=[{"xaxis.visible": True, "yaxis.visible": True}],
            args2=[{"xaxis.visible": False, "yaxis.visible": False}],
        )],
        x=0.98, xanchor="right", y=0.19, yanchor="bottom",  # Bottom right, above corner labels
        showactive=False,
        bgcolor="rgba(26,26,26,0.95)", bordercolor="rgba(150,150,150,0.4)", borderwidth=1,
        pad=dict(r=4, l=4, t=4, b=4), font=dict(size=11, color="rgba(150,150,150,0.9)"),
    )
    print("✓ Created zone badges toggle button")
    print("✓ Created corner labels toggle button")
    print("✓ Created axes toggle button")
    print()

    # 10) Layout: add zone pills, zone badges toggle, corner labels toggle, and axes toggle, use legend for drivers
    print("Finalizing layout...")
    fig.update_layout(
        title=dict(
            text="Barber Motorsports Park",
            y=0.95,
            yanchor="top",
            x=0.5,
            xanchor="center",
        ),
        updatemenus=[
            dict(  # Zone pills
                type="buttons", direction="right", buttons=zone_buttons,
                x=0.5, xanchor="center", y=0.88, yanchor="bottom",
                showactive=True, active=0,  # "Full" is first button, default view
                bgcolor="rgba(26,26,26,0.95)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1,
                pad=dict(r=4, l=4, t=4, b=4), font=dict(size=11, color="white"),
            ),
            zone_badges_toggle_button,  # Zone badges toggle
            corner_toggle_button,  # Corner labels toggle
            axes_toggle_button,  # Axes toggle
        ],
        legend=dict(
            x=0.98, xanchor="right", y=0.95, yanchor="top",
            bgcolor="rgba(20,20,20,0.9)", bordercolor="rgba(255,255,255,0.3)", borderwidth=1,
            font=dict(size=10, color="white"),
            itemclick="toggle", itemdoubleclick="toggleothers",
        ),
        autosize=True,
        margin=dict(l=0, r=0, t=10, b=0),
    )

    # 11) Initial camera to Full view
    fig.update_xaxes(range=[full_x_min, full_x_max], visible=False)
    fig.update_yaxes(range=[full_y_min, full_y_max], visible=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(
        output_path,
        config={"responsive": True},
        default_width='100%',
        default_height='100%'
    )

    # 12) Inject fullscreen CSS and keyboard navigation JavaScript
    print("Adding keyboard navigation...")
    html_content = output_path.read_text()

    fullscreen_css = """
    <style>
    html {
        margin: 0;
        padding: 0;
        overflow: hidden;
        width: 100%;
        height: 100%;
    }
    body {
        margin: 0;
        padding: 0;
        overflow: hidden;
        width: 100%;
        height: 100%;
    }
    body > div {
        width: 100%;
        height: 100%;
    }
    .plotly-graph-div {
        width: 100vw !important;
        height: 100vh !important;
    }
    </style>
    """

    keyboard_script = """
    <script>
    // Fix active zone button text color (black on white background)
    function updateZoneButtonStyles() {
        const updateMenus = document.querySelectorAll('.updatemenu-button');
        if (updateMenus.length === 0) return;

        const zonePills = Array.from(updateMenus).slice(0, 9);  // Full + Z1-Z8

        zonePills.forEach((btn) => {
            if (btn.classList.contains('active')) {
                // Active button: black text on white background
                btn.style.setProperty('color', 'black', 'important');
                btn.style.setProperty('background-color', 'rgba(255,255,255,0.95)', 'important');
            } else {
                // Inactive button: white text on dark background
                btn.style.setProperty('color', 'white', 'important');
                btn.style.setProperty('background-color', 'rgba(26,26,26,0.95)', 'important');
            }
        });
    }

    // Update styles on page load
    setTimeout(updateZoneButtonStyles, 100);

    // Update styles when buttons are clicked
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('updatemenu-button')) {
            setTimeout(updateZoneButtonStyles, 50);
        }
    });

    // Animation state tracking to prevent queueing
    let isAnimating = false;

    // Smooth zoom animation using requestAnimationFrame
    function smoothZoom(plotDiv, targetRanges, duration, callback) {
        // Get current ranges
        const layout = plotDiv._fullLayout;
        const fromX = [layout.xaxis.range[0], layout.xaxis.range[1]];
        const fromY = [layout.yaxis.range[0], layout.yaxis.range[1]];
        const toX = targetRanges['xaxis.range'];
        const toY = targetRanges['yaxis.range'];

        const startTime = performance.now();

        function step(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1.0);

            // Cubic-in-out easing function
            const eased = progress < 0.5
                ? 4 * progress * progress * progress
                : 1 - Math.pow(-2 * progress + 2, 3) / 2;

            // Interpolate axis ranges
            const currentRanges = {
                'xaxis.range': [
                    fromX[0] + (toX[0] - fromX[0]) * eased,
                    fromX[1] + (toX[1] - fromX[1]) * eased
                ],
                'yaxis.range': [
                    fromY[0] + (toY[0] - fromY[0]) * eased,
                    fromY[1] + (toY[1] - fromY[1]) * eased
                ]
            };

            Plotly.relayout(plotDiv, currentRanges);

            if (progress < 1.0) {
                requestAnimationFrame(step);
            } else {
                if (callback) callback();
            }
        }

        requestAnimationFrame(step);
    }

    // Keyboard navigation with smooth zoom transitions
    document.addEventListener('keydown', function(e) {
        // Don't interfere with input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        // Prevent animation queueing when users spam keys
        if (isAnimating) {
            return;
        }

        // Get the Plotly plot div
        const plotDiv = document.querySelector('.plotly-graph-div');
        if (!plotDiv || !plotDiv._fullLayout || !plotDiv._fullLayout.updatemenus) {
            return;
        }

        // Get current active button index from Plotly's layout
        const currentActive = plotDiv._fullLayout.updatemenus[0].active;
        const maxIndex = plotDiv._fullLayout.updatemenus[0].buttons.length - 1;
        let newIndex = currentActive;

        // Arrow key navigation
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            newIndex = (currentActive + 1) % (maxIndex + 1);  // Wrap around
            e.preventDefault();
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            newIndex = (currentActive - 1 + maxIndex + 1) % (maxIndex + 1);  // Wrap around
            e.preventDefault();
        } else {
            return;  // Not an arrow key
        }

        // Execute the button's action with smooth animation
        if (newIndex !== currentActive) {
            const menu = plotDiv._fullLayout.updatemenus[0];
            const button = menu.buttons[newIndex];

            // Execute the button's relayout action with smooth transition
            if (button.method === 'relayout' && button.args && button.args[0]) {
                isAnimating = true;

                // Smooth zoom animation over 500ms
                smoothZoom(plotDiv, button.args[0], 500, function() {
                    // Update active button state after animation completes
                    Plotly.relayout(plotDiv, {'updatemenus[0].active': newIndex});
                    setTimeout(updateZoneButtonStyles, 50);
                    isAnimating = false;
                });
            } else {
                // Fallback: just update active state
                Plotly.relayout(plotDiv, {'updatemenus[0].active': newIndex});
                setTimeout(updateZoneButtonStyles, 50);
            }
        }
    });
    </script>
    """

    # Remove fixed width/height inline styles from plotly div
    import re
    html_content = re.sub(
        r'(<div[^>]*class="plotly-graph-div"[^>]*)\s*style="[^"]*"',
        r'\1',
        html_content
    )

    # Insert CSS into head and script before closing </body>
    html_content = html_content.replace('</head>', fullscreen_css + '\n</head>')
    html_content = html_content.replace('</body>', keyboard_script + '\n</body>')
    output_path.write_text(html_content)

    print(f"✓ Saved zone-focused dashboard to: {output_path}")
    print("✓ Added keyboard navigation (arrow keys to cycle zones)")
    print("✓ Added active button styling (black text on white background)")
    print("✓ Added fullscreen CSS (no margins, fills viewport)")
    print()

    return fig
