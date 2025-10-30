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
                    font=dict(size=12, color="black", family="Arial Black"),
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
            bgcolor="rgba(20, 20, 20, 0.9)",
            bordercolor="rgba(255, 255, 255, 0.3)",
            borderwidth=2,
            pad={"r": 10, "t": 6},
            font=dict(size=11, color="white"),
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

    # 4) Zone boundary rectangles
    print("Adding zone boundary rectangles...")
    for zid in zone_order:
        zb = zone_bounds[zid]
        fig.add_shape(
            type="rect",
            x0=zb["x_min"], y0=zb["y_min"], x1=zb["x_max"], y1=zb["y_max"],
            line=dict(color="rgba(255,255,255,0.2)", width=2, dash="dash"),
            layer="below",
        )
    print(f"✓ Added {len(zone_order)} zone rectangles")
    print()

    # 5) Zone badges
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
        ))
    print(f"✓ Added {len(ref_brakes['zone_id'].dropna().unique())} zone badges")
    print()

    # 6) Reference trace (white, all zones)
    print("Adding reference driver brake points...")
    fig.add_trace(go.Scatter(
        x=ref_brakes["x_meters"], y=ref_brakes["y_meters"],
        mode="markers",
        marker=dict(size=8, color="rgba(255,255,255,0.6)", line=dict(color="rgba(255,255,255,0.8)", width=2)),
        name=f"Reference #{reference_vehicle_number}",
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
            name=f"Driver #{drv}",
            hovertemplate=f"#{drv} x: %{{x:.1f}}m<br>y: %{{y:.1f}}m<extra></extra>",
            visible=False,  # hidden by default
        ))
    print(f"✓ Added traces for {len(driver_list)} drivers")
    print()

    # 8) Zone pills (relayout only)
    print("Creating zone selector pills...")
    zone_buttons = []
    first_zone = zone_order[0] if zone_order else 1
    for zid in zone_order:
        zb = zone_bounds[zid]
        zone_buttons.append(dict(
            label=f"Z{zid}",
            method="relayout",
            args=[{
                "xaxis.range": [zb["x_min"], zb["x_max"]],
                "yaxis.range": [zb["y_min"], zb["y_max"]],
            }],
        ))
    print(f"✓ Created {len(zone_buttons)} zone pill buttons")
    print()

    # 9) Driver chips (visibility only)
    print("Creating driver selector chips...")
    # Find indices of reference trace and first driver trace
    # Traces: track surface (1) + centerline (1) + zone badges (8) + shapes don't count + ref (1) + drivers (N)
    # We need to count actual traces in fig.data
    base_trace_count = len(fig.data) - len(driver_list)  # Everything except driver traces
    ref_trace_idx = base_trace_count - 1  # Reference is last before drivers
    first_driver_idx = base_trace_count

    def visible_for_ref_only():
        vis = [True] * len(fig.data)
        # Hide all driver traces
        for i in range(first_driver_idx, len(fig.data)):
            vis[i] = False
        return vis

    def visible_for_driver_index(driver_idx):
        vis = [True] * len(fig.data)
        # Hide all drivers except selected
        for j in range(len(driver_list)):
            vis[first_driver_idx + j] = (j == driver_idx)
        return vis

    driver_buttons = [dict(
        label="Reference Only",
        method="update",
        args=[{"visible": visible_for_ref_only()}],
    )]

    for idx, drv in enumerate(driver_list):
        drv_info = valid[valid["vehicle_number"] == drv].iloc[0]
        lap_time = drv_info["fastest_lap_time"]
        driver_buttons.append(dict(
            label=f"+ Driver #{drv} ({lap_time})",
            method="update",
            args=[{"visible": visible_for_driver_index(idx)}],
        ))
    print(f"✓ Created {len(driver_buttons)} driver chip buttons")
    print()

    # 10) Layout: remove pit lane traces if any; add menus
    print("Finalizing layout...")
    fig.update_layout(
        title=f"Barber — Zone-Focused View<br><sub>Reference #{reference_vehicle_number} (white) + optional driver</sub>",
        updatemenus=[
            dict(  # Zone pills
                type="buttons", direction="right", buttons=zone_buttons,
                x=0.5, xanchor="center", y=1.02, yanchor="top",
                showactive=True, active=zone_order.index(first_zone) if zone_order else 0,
                bgcolor="rgba(26,26,26,0.95)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1,
                pad=dict(r=4, l=4, t=4, b=4), font=dict(size=12, color="white"),
            ),
            dict(  # Driver chips
                type="buttons", direction="right", buttons=driver_buttons,
                x=0.5, xanchor="center", y=0.98, yanchor="top",
                showactive=True, active=0,
                bgcolor="rgba(26,26,26,0.95)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1,
                pad=dict(r=4, l=4, t=4, b=4), font=dict(size=12, color="white"),
            ),
        ],
        legend=dict(x=0.02, y=0.88, bgcolor="rgba(20,20,20,0.8)", bordercolor="rgba(255,255,255,0.3)", borderwidth=1),
    )

    # 11) Initial camera to Zone 1
    if zone_order:
        zb = zone_bounds[first_zone]
        fig.update_xaxes(range=[zb["x_min"], zb["x_max"]])
        fig.update_yaxes(range=[zb["y_min"], zb["y_max"]])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"✓ Saved zone-focused dashboard to: {output_path}")
    print()

    return fig
