# ABOUTME: Interactive Plotly dashboards for brake point analysis and zone comparison
# ABOUTME: Zone-focused view with pills, toggles, rotation, and keyboard navigation

import json

import numpy as np
import plotly.graph_objects as go
from pathlib import Path

from .track_outline import make_base_track_figure
from .geometry import rotate_coordinates
from ..data_processing import compute_zone_bounds


# Driver colors - large qualitative palette with distinct hues
# Combines D3 Category10 + Category20 for up to 30 unique drivers
_DRIVER_PALETTE = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
    "#aec7e8",
    "#ffbb78",
    "#98df8a",
    "#ff9896",
    "#c5b0d5",
    "#c49c94",
    "#f7b6d2",
    "#c7c7c7",
    "#dbdb8d",
    "#9edae5",
    "#393b79",
    "#637939",
    "#8c6d31",
    "#843c39",
    "#7b4173",
    "#5254a3",
    "#8ca252",
    "#bd9e39",
    "#ad494a",
    "#a55194",
]


def _get_driver_color(vehicle_number):
    """Return color for a driver, cycling through palette if needed."""
    return _DRIVER_PALETTE[(vehicle_number - 1) % len(_DRIVER_PALETTE)]


# Build lookup dict for all reasonable vehicle numbers (1-99)
DRIVER_COLORS = {i: _get_driver_color(i) for i in range(1, 100)}


def _add_centerline_direction_arrows(
    fig,
    spacing_m=30.0,
    arrow_length_m=5.0,
    arrow_width_m=2.0,
    color="rgba(92,207,255,0.5)",
):
    """
    Add small triangular direction indicators along the centerline using shapes.

    Shapes render reliably in HTML and survive layout updates (unlike annotations).
    Uses SVG paths to create filled triangles pointing in the direction of travel.

    Args:
        fig: Plotly figure object with Centerline trace
        spacing_m: Target spacing between arrows in meters (default: 30.0)
        arrow_length_m: Length of arrow from base to tip in meters (default: 5.0)
        arrow_width_m: Width of arrow base in meters (default: 2.0)
        color: Fill color for arrows (default: semi-transparent cyan)
    """
    # Find the centerline trace
    centerline_trace = None
    for trace in fig.data:
        if (
            hasattr(trace, "name")
            and trace.name == "Centerline"
            and trace.mode == "lines"
        ):
            centerline_trace = trace
            break

    if centerline_trace is None:
        print("⚠ Centerline trace not found, skipping direction arrows")
        return

    # Extract coordinates as numpy arrays
    x = np.array(centerline_trace.x)
    y = np.array(centerline_trace.y)

    # If closed track (first equals last), remove duplicate last point
    if len(x) > 1 and x[0] == x[-1] and y[0] == y[-1]:
        x = x[:-1]
        y = y[:-1]

    n = len(x)
    if n < 3:
        print("⚠ Centerline too short for direction arrows")
        return

    # Compute segment lengths
    dx = np.diff(x)
    dy = np.diff(y)
    segment_lengths = np.sqrt(dx**2 + dy**2)
    median_step = np.median(segment_lengths)

    # Calculate stride based on desired spacing
    stride = max(1, round(spacing_m / median_step))

    # Generate arrows at stride intervals
    arrow_count = 0
    shapes = list(fig.layout.shapes) if fig.layout.shapes else []

    for i in range(0, n, stride):
        # Compute tangent using central difference with wraparound
        i_prev = (i - 1) % n
        i_next = (i + 1) % n
        tx = x[i_next] - x[i_prev]
        ty = y[i_next] - y[i_prev]

        # Normalize tangent
        t_mag = np.sqrt(tx**2 + ty**2)
        if t_mag < 1e-6:
            continue  # Skip degenerate points
        tx /= t_mag
        ty /= t_mag

        # Compute normal (perpendicular to tangent)
        nx = -ty
        ny = tx

        # Define triangle vertices
        # Tip: move forward along tangent
        tip_x = x[i] + 0.5 * arrow_length_m * tx
        tip_y = y[i] + 0.5 * arrow_length_m * ty

        # Base center: move backward along tangent
        base_x = x[i] - 0.5 * arrow_length_m * tx
        base_y = y[i] - 0.5 * arrow_length_m * ty

        # Left and right base points
        left_x = base_x + 0.5 * arrow_width_m * nx
        left_y = base_y + 0.5 * arrow_width_m * ny
        right_x = base_x - 0.5 * arrow_width_m * nx
        right_y = base_y - 0.5 * arrow_width_m * ny

        # Build SVG path: M (tip) L (left) L (right) Z (close)
        path = f"M {tip_x},{tip_y} L {left_x},{left_y} L {right_x},{right_y} Z"

        # Add shape to figure
        shapes.append(
            dict(
                type="path",
                path=path,
                xref="x",
                yref="y",
                fillcolor=color,
                line=dict(width=0),
                layer="above",
            )
        )
        arrow_count += 1

    # Update figure with all shapes
    fig.update_layout(shapes=shapes)
    print(
        f"✓ Added {arrow_count} direction arrows along centerline (spacing ~{spacing_m}m)"
    )


def create_zone_focused_dashboard(
    telemetry_df,
    brake_events_df,
    driver_summary_df,
    centroids_df,
    reference_vehicle_number,
    output_path,
    centerline_path=None,
    corner_labels_json=None,
):
    """
    Create zone-focused interactive dashboard with zone pills and driver chips.

    Shows one zone at a time via horizontal zone pills.
    Uses axis range cropping (relayout) instead of trace visibility per zone.
    Reference points in white, comparison drivers each in consistent driver colors.

    Args:
        telemetry_df: Full telemetry DataFrame for track rendering
        brake_events_df: Brake events DataFrame
        driver_summary_df: Driver summary with lap times
        centroids_df: Zone centroids DataFrame (average brake points per driver per zone)
        reference_vehicle_number: Vehicle number of reference driver
        output_path: Path to save HTML file
        centerline_path: Optional path to centerline CSV (loads if exists)
        corner_labels_json: Optional path to corner labels JSON

    Returns:
        Plotly figure object
    """
    print(f"Creating zone-focused dashboard (reference #{reference_vehicle_number})...")
    print()

    # 1) Track outline
    print("Generating track outline...")
    print("-" * 80)
    _, _, fig = make_base_track_figure(
        telemetry_df,
        centerline_path=centerline_path,
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

    # Add direction arrows to centerline
    _add_centerline_direction_arrows(
        fig, spacing_m=75.0, arrow_length_m=5.0, arrow_width_m=2.0
    )
    print()

    # Rotate brake event coordinates
    brake_events_df = brake_events_df.copy()
    x_rot, y_rot = rotate_coordinates(
        brake_events_df["x_meters"].values,
        brake_events_df["y_meters"].values,
        rotation_angle,
    )
    brake_events_df["x_meters"] = x_rot
    brake_events_df["y_meters"] = y_rot
    print("✓ Rotated brake event coordinates")

    # Rotate centroid coordinates
    centroids_df = centroids_df.copy()
    x_rot_cent, y_rot_cent = rotate_coordinates(
        centroids_df["centroid_x"].values,
        centroids_df["centroid_y"].values,
        rotation_angle,
    )
    centroids_df["centroid_x"] = x_rot_cent
    centroids_df["centroid_y"] = y_rot_cent
    print("✓ Rotated centroid coordinates")
    print()

    # 2) Compute zone bboxes
    print("Computing zone boundaries...")
    zone_bounds = compute_zone_bounds(brake_events_df, padding_m=20.0)
    zone_order = sorted(zone_bounds.keys())
    print(f"✓ Calculated boundaries for {len(zone_order)} zones")
    print()

    # 2.5) Compute zone centers for labels
    print("Computing zone centers for labels...")
    zone_centers = {}
    ref_brake_df = brake_events_df[
        brake_events_df["vehicle_number"] == reference_vehicle_number
    ]
    for zid in zone_order:
        zone_points = ref_brake_df[ref_brake_df["zone_id"] == zid]
        if len(zone_points) > 0:
            # Use mean of reference driver's brake points in this zone
            cx = zone_points["x_meters"].mean()
            cy = zone_points["y_meters"].mean()
            zone_centers[zid] = (cx, cy)
        else:
            # Fallback to geometric center of zone bounds
            zb = zone_bounds[zid]
            cx = (zb["x_min"] + zb["x_max"]) / 2
            cy = (zb["y_min"] + zb["y_max"]) / 2
            zone_centers[zid] = (cx, cy)
    print(f"✓ Calculated centers for {len(zone_centers)} zones")
    print()

    # 3) Corner labels (1-17)
    print("Loading corner labels...")
    if corner_labels_json and Path(corner_labels_json).exists():
        corner_labels = json.loads(Path(corner_labels_json).read_text())
        corner_x = [c["x_meters"] for c in corner_labels]
        corner_y = [c["y_meters"] for c in corner_labels]
        corner_text = [c["label"] for c in corner_labels]

        # Rotate corner labels
        corner_x_rot, corner_y_rot = rotate_coordinates(
            corner_x, corner_y, rotation_angle
        )

        fig.add_trace(
            go.Scatter(
                x=corner_x_rot,
                y=corner_y_rot,
                mode="markers+text",
                marker=dict(
                    size=24,
                    color="rgba(255,255,255,0.15)",
                    line=dict(color="rgba(255,165,0,0.8)", width=2),
                ),
                text=corner_text,
                textposition="middle center",
                textfont=dict(size=10, color="orange", family="Arial Black"),
                name="Track Corners",
                showlegend=False,
                hovertemplate="Corner %{text}<extra></extra>",
                visible=True,
            )
        )
        print(f"✓ Added {len(corner_labels)} corner labels")
    else:
        print("⚠ Corner labels file not found, skipping")
    print()

    # 4) All driver traces (including winner), colored by driver
    print("Preparing driver brake point traces...")
    valid = driver_summary_df.dropna(subset=["fastest_lap_seconds"]).sort_values(
        "fastest_lap_seconds"
    )
    driver_list = [int(v) for v in valid["vehicle_number"].tolist()]

    for drv in driver_list:
        df_drv = brake_events_df[
            (brake_events_df["vehicle_number"] == drv)
            & (brake_events_df["zone_id"].notna())
        ].copy()

        # Winner gets white fill with gold stroke (championship styling)
        is_winner = drv == reference_vehicle_number
        if is_winner:
            driver_color = "rgba(255, 255, 255, 1.0)"  # Pure white fill
            marker_line_color = "rgba(255, 215, 0, 1.0)"  # Gold stroke
            marker_line_width = 4  # Thick gold ring
            is_visible = True
            driver_label = f"Winner #{drv}"
        else:
            driver_color = DRIVER_COLORS.get(drv, "#999")
            marker_line_color = "rgba(255,255,255,0.7)"
            marker_line_width = 2
            is_visible = "legendonly"
            driver_label = f"#{drv}"

        lap_time = valid[valid["vehicle_number"] == drv].iloc[0]["fastest_lap_time"]

        fig.add_trace(
            go.Scatter(
                x=df_drv["x_meters"],
                y=df_drv["y_meters"],
                mode="markers",
                marker=dict(
                    size=10,
                    color=driver_color,
                    opacity=1.0,
                    line=dict(color=marker_line_color, width=marker_line_width),
                ),
                name=f"{driver_label} ({lap_time})",
                hovertemplate=f"#{drv} x: %{{x:.1f}}m<br>y: %{{y:.1f}}m<extra></extra>",
                visible=is_visible,
                showlegend=True,
            )
        )
    print(
        f"✓ Added brake point traces for {len(driver_list)} drivers (winner visible by default)"
    )
    print()

    # 5) Add centroid traces (average brake points per driver per zone)
    print("Preparing centroid traces (average brake points)...")
    for drv in driver_list:
        df_cent = centroids_df[centroids_df["vehicle_number"] == drv].copy()

        # Winner gets white fill with gold stroke, same as brake points
        is_winner = drv == reference_vehicle_number
        if is_winner:
            driver_color = "rgba(255, 255, 255, 1.0)"  # Pure white fill
            marker_line_color = "rgba(255, 215, 0, 1.0)"  # Gold stroke
            marker_line_width = 4  # Thick gold ring
        else:
            driver_color = DRIVER_COLORS.get(drv, "#999")
            marker_line_color = "rgba(255,255,255,0.7)"
            marker_line_width = 2

        fig.add_trace(
            go.Scatter(
                x=df_cent["centroid_x"],
                y=df_cent["centroid_y"],
                mode="markers",
                marker=dict(
                    size=20,  # Same size for all drivers
                    color=driver_color,
                    opacity=0,  # Initially hidden (controlled by mode toggle)
                    line=dict(color=marker_line_color, width=marker_line_width),
                ),
                name=f"#{drv} (avg)",  # Not shown in legend
                hovertemplate=f"#{drv} avg x: %{{x:.1f}}m<br>y: %{{y:.1f}}m<extra></extra>",
                showlegend=False,  # Don't show in legend
            )
        )
    print(f"✓ Added centroid traces for {len(driver_list)} drivers")
    print()

    # 6) Add zone label traces (badges) - rendered on top of all other traces
    print("Adding zone label badges...")
    zone_label_count = 0
    for zid in zone_order:
        if zid in zone_centers:
            cx, cy = zone_centers[zid]
            fig.add_trace(
                go.Scatter(
                    x=[cx],
                    y=[cy],
                    mode="markers+text",
                    marker=dict(
                        size=28,
                        color="rgba(255,255,255,0.95)",
                        line=dict(color="rgba(160,160,160,1)", width=3),
                    ),
                    text=[f"Z{int(zid)}"],
                    textposition="middle center",
                    textfont=dict(size=11, color="black", family="Arial Black"),
                    name=f"Zone Label Z{int(zid)}",
                    meta="zone-badge",
                    showlegend=False,
                    hoverinfo="skip",
                    visible=False,  # Initially hidden
                )
            )
            zone_label_count += 1
    print(f"✓ Added {zone_label_count} zone label badges (initially hidden)")
    print()

    # 7) Zone pills (relayout only)
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
    zone_buttons.append(
        dict(
            label="Full",
            method="relayout",
            args=[
                {
                    "xaxis.range": [full_x_min, full_x_max],
                    "yaxis.range": [full_y_min, full_y_max],
                }
            ],
        )
    )

    # Add zone-specific buttons
    for zid in sorted(zone_bounds.keys()):
        zb = zone_bounds[zid]
        zone_buttons.append(
            dict(
                label=f"Z{zid}",
                method="relayout",
                args=[
                    {
                        "xaxis.range": [zb["x_min"], zb["x_max"]],
                        "yaxis.range": [zb["y_min"], zb["y_max"]],
                    }
                ],
            )
        )
    print(
        f"✓ Created {len(zone_buttons)} zone pill buttons (Full + {len(zone_bounds)} zones)"
    )
    print()

    # 8) Corner labels, centroids, and axes toggle buttons
    print("Creating toggle buttons for labels...")
    # Trace structure: [track, centerline, corner_labels, drivers..., centroids..., zone_labels...]
    corner_labels_idx = 2  # Third trace (after track and centerline)
    first_driver_idx = 3  # Drivers start after corner_labels
    first_centroid_idx = 3 + len(driver_list)  # Centroids start after all drivers
    # Zone labels are at the end (found dynamically via meta='zone-badge')

    corner_toggle_button = dict(
        type="buttons",
        direction="right",
        buttons=[
            dict(
                label="Corner Labels",
                method="restyle",
                args=[{"visible": True}, [corner_labels_idx]],
                args2=[{"visible": False}, [corner_labels_idx]],
            )
        ],
        x=0.98,
        xanchor="right",
        y=0.13,
        yanchor="bottom",
        showactive=False,
        bgcolor="rgba(26,26,26,0.95)",
        bordercolor="rgba(255,165,0,0.4)",
        borderwidth=1,
        pad=dict(r=4, l=4, t=4, b=4),
        font=dict(size=11, color="orange"),
    )

    centroids_toggle_button = dict(
        type="buttons",
        direction="right",
        buttons=[
            dict(
                label="Average Brake Points",
                method="skip",  # Don't do anything automatically, JavaScript will handle it
            )
        ],
        x=0.98,
        xanchor="right",
        y=0.07,
        yanchor="bottom",
        showactive=False,
        bgcolor="rgba(26,26,26,0.95)",
        bordercolor="rgba(255,165,0,0.4)",
        borderwidth=1,
        pad=dict(r=4, l=4, t=4, b=4),
        font=dict(size=11, color="orange"),
    )

    axes_toggle_button = dict(
        type="buttons",
        direction="right",
        buttons=[
            dict(
                label="Axes",
                method="relayout",
                args=[{"xaxis.visible": True, "yaxis.visible": True}],
                args2=[{"xaxis.visible": False, "yaxis.visible": False}],
            )
        ],
        x=0.98,
        xanchor="right",
        y=0.19,
        yanchor="bottom",
        showactive=False,
        bgcolor="rgba(26,26,26,0.95)",
        bordercolor="rgba(150,150,150,0.4)",
        borderwidth=1,
        pad=dict(r=4, l=4, t=4, b=4),
        font=dict(size=11, color="rgba(150,150,150,0.9)"),
    )

    # Zone labels toggle button (only add if zone labels exist)
    zone_labels_toggle_button = None
    if zone_label_count > 0:
        zone_labels_toggle_button = dict(
            type="buttons",
            direction="right",
            buttons=[
                dict(
                    label="Zone Labels",
                    method="skip",  # JavaScript will handle the toggle
                )
            ],
            x=0.98,
            xanchor="right",
            y=0.01,
            yanchor="bottom",
            showactive=False,
            bgcolor="rgba(26,26,26,0.95)",
            bordercolor="rgba(255,165,0,0.4)",
            borderwidth=1,
            pad=dict(r=4, l=4, t=4, b=4),
            font=dict(size=11, color="orange"),
        )

    print("✓ Created corner labels toggle button")
    print("✓ Created average brake points toggle button")
    print("✓ Created axes toggle button")
    if zone_labels_toggle_button:
        print("✓ Created zone labels toggle button")
    print()

    # 9) Layout: add toggles (zone pills moved to external toolbar), use legend for drivers
    print("Finalizing layout...")
    # Build updatemenus list conditionally
    updatemenus_list = [
        corner_toggle_button,
        centroids_toggle_button,
        axes_toggle_button,
    ]
    if zone_labels_toggle_button:
        updatemenus_list.append(zone_labels_toggle_button)

    fig.update_layout(
        title=dict(
            text="Barber Motorsports Park",
            y=0.95,
            yanchor="top",
            x=0.5,
            xanchor="center",
        ),
        annotations=[
            dict(
                text="← → Navigate zones with arrow keys",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.985,
                xanchor="center",
                yanchor="bottom",
                showarrow=False,
                font=dict(size=10, color="rgba(255, 255, 255, 0.5)"),
            )
        ],
        updatemenus=updatemenus_list,
        legend=dict(
            x=0.98,
            xanchor="right",
            y=0.84,
            yanchor="top",
            bgcolor="rgba(20,20,20,0.9)",
            bordercolor="rgba(255,255,255,0.3)",
            borderwidth=1,
            font=dict(size=10, color="white"),
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        dragmode="pan",
        hovermode="closest",
        uirevision="zone-dashboard-v1",
        autosize=True,
        margin=dict(l=0, r=0, t=60, b=0),
    )

    # 10) Initial camera to Full view
    fig.update_xaxes(range=[full_x_min, full_x_max], visible=False)
    fig.update_yaxes(range=[full_y_min, full_y_max], visible=False)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(
        output_path,
        config={"responsive": True, "displayModeBar": False},
        default_width="100%",
        default_height="100%",
    )

    # 11) Generate external toolbar HTML with zone pill buttons
    print("Generating external zone pill toolbar...")

    # Build toolbar HTML
    toolbar_buttons_html = []
    for i, btn in enumerate(zone_buttons):
        active_class = "active" if i == 0 else ""  # "Full" is active by default
        toolbar_buttons_html.append(
            f'<button class="zone-pill {active_class}" data-zone-index="{i}">{btn["label"]}</button>'
        )

    toolbar_html = f"""
    <div id="dashboard-toolbar">
        <div class="zone-pills-container">
            {"".join(toolbar_buttons_html)}
        </div>
    </div>
    """

    # Convert zone_buttons to JavaScript data
    zone_data_js = (
        "const ZONE_DATA = "
        + json.dumps(
            [
                {
                    "label": btn["label"],
                    "xRange": btn["args"][0]["xaxis.range"],
                    "yRange": btn["args"][0]["yaxis.range"],
                }
                for btn in zone_buttons
            ]
        )
        + ";\n"
    )
    print(f"✓ Generated toolbar with {len(zone_buttons)} zone pill buttons")
    print()

    # 12) Inject wrapper structure, fullscreen CSS, and keyboard navigation JavaScript
    print("Adding keyboard navigation...")
    html_content = output_path.read_text()

    fullscreen_css = """
    <style>
    html, body {
        margin: 0;
        padding: 0;
        overflow: hidden;
        width: 100%;
        height: 100%;
    }
    #plot-wrapper {
        display: flex;
        flex-direction: column;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
    }
    #dashboard-toolbar {
        flex-shrink: 0;
        background: rgba(20, 20, 20, 0.95);
        padding: 10px;
        display: flex;
        justify-content: center;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .zone-pills-container {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        justify-content: center;
    }
    .zone-pill {
        background: rgba(26, 26, 26, 0.95);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        font-family: Arial, sans-serif;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .zone-pill:hover {
        background: rgba(40, 40, 40, 0.95);
        border-color: rgba(255, 255, 255, 0.3);
    }
    .zone-pill.active {
        background: rgba(255, 255, 255, 0.95);
        color: black;
        border-color: rgba(255, 255, 255, 0.5);
    }
    .plotly-graph-div {
        flex: 1;
        min-height: 0;
    }
    </style>
    """

    keyboard_script = f"""
    <script>
    // Zone data for external toolbar buttons
    {zone_data_js}

    // Driver and centroid trace mapping
    // Trace structure: [track, centerline, corner_labels, drivers..., centroids..., zone_labels...]
    const NUM_DRIVERS = {len(driver_list)};
    const FIRST_DRIVER_IDX = {first_driver_idx};
    const FIRST_CENTROID_IDX = {first_centroid_idx};

    // Current active zone index
    let activeZoneIndex = 0;

    // Animation state tracking to prevent queueing
    let isAnimating = false;

    // Display mode: 'points' (brake points visible) or 'centroids' (centroids visible)
    let displayMode = 'points';

    // Update active button styling
    function updateActiveZoneButton(newIndex) {{
        const buttons = document.querySelectorAll('.zone-pill');
        buttons.forEach((btn, idx) => {{
            if (idx === newIndex) {{
                btn.classList.add('active');
            }} else {{
                btn.classList.remove('active');
            }}
        }});
        activeZoneIndex = newIndex;
    }}

    // Smooth zoom animation using requestAnimationFrame
    function smoothZoom(plotDiv, targetRanges, duration, callback) {{
        // Get current ranges
        const layout = plotDiv._fullLayout;
        const fromX = [layout.xaxis.range[0], layout.xaxis.range[1]];
        const fromY = [layout.yaxis.range[0], layout.yaxis.range[1]];
        const toX = targetRanges['xaxis.range'];
        const toY = targetRanges['yaxis.range'];

        const startTime = performance.now();

        function step(currentTime) {{
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1.0);

            // Cubic-in-out easing function
            const eased = progress < 0.5
                ? 4 * progress * progress * progress
                : 1 - Math.pow(-2 * progress + 2, 3) / 2;

            // Interpolate axis ranges
            const currentRanges = {{
                'xaxis.range': [
                    fromX[0] + (toX[0] - fromX[0]) * eased,
                    fromX[1] + (toX[1] - fromX[1]) * eased
                ],
                'yaxis.range': [
                    fromY[0] + (toY[0] - fromY[0]) * eased,
                    fromY[1] + (toY[1] - fromY[1]) * eased
                ]
            }};

            Plotly.relayout(plotDiv, currentRanges);

            if (progress < 1.0) {{
                requestAnimationFrame(step);
            }} else {{
                if (callback) callback();
            }}
        }}

        requestAnimationFrame(step);
    }}

    // Navigate to zone by index
    function navigateToZone(zoneIndex) {{
        if (isAnimating || zoneIndex === activeZoneIndex) return;

        const plotDiv = document.querySelector('.plotly-graph-div');
        if (!plotDiv || !plotDiv._fullLayout) return;

        const zoneData = ZONE_DATA[zoneIndex];
        const targetRanges = {{
            'xaxis.range': zoneData.xRange,
            'yaxis.range': zoneData.yRange
        }};

        isAnimating = true;
        smoothZoom(plotDiv, targetRanges, 500, function() {{
            updateActiveZoneButton(zoneIndex);
            isAnimating = false;
        }});
    }}

    // Toggle between brake points and centroids (mutually exclusive)
    function toggleCentroids() {{
        const plotDiv = document.querySelector('.plotly-graph-div');
        if (!plotDiv || !plotDiv._fullLayout) return;

        // Toggle display mode
        displayMode = displayMode === 'points' ? 'centroids' : 'points';

        const traces = plotDiv.data;

        if (displayMode === 'centroids') {{
            // Switch to centroid mode: hide brake points, show centroids
            const brakeOpacities = [];
            const centroidOpacities = [];
            const brakeIndices = [];
            const centroidIndices = [];

            for (let i = 0; i < NUM_DRIVERS; i++) {{
                const driverIdx = FIRST_DRIVER_IDX + i;
                const centroidIdx = FIRST_CENTROID_IDX + i;
                const driverTrace = traces[driverIdx];

                brakeIndices.push(driverIdx);
                brakeOpacities.push(0);  // Hide all brake points

                centroidIndices.push(centroidIdx);
                // Show centroid only if driver is visible
                centroidOpacities.push(driverTrace.visible === true ? 1 : 0);
            }}

            // Batch update opacities
            Plotly.restyle(plotDiv, {{'marker.opacity': brakeOpacities}}, brakeIndices);
            Plotly.restyle(plotDiv, {{'marker.opacity': centroidOpacities}}, centroidIndices);
        }} else {{
            // Switch to points mode: show brake points, hide centroids
            const brakeOpacities = [];
            const centroidOpacities = [];
            const brakeIndices = [];
            const centroidIndices = [];

            for (let i = 0; i < NUM_DRIVERS; i++) {{
                const driverIdx = FIRST_DRIVER_IDX + i;
                const centroidIdx = FIRST_CENTROID_IDX + i;

                brakeIndices.push(driverIdx);
                brakeOpacities.push(1);  // Show all brake points

                centroidIndices.push(centroidIdx);
                centroidOpacities.push(0);  // Hide all centroids
            }}

            // Batch update opacities
            Plotly.restyle(plotDiv, {{'marker.opacity': brakeOpacities}}, brakeIndices);
            Plotly.restyle(plotDiv, {{'marker.opacity': centroidOpacities}}, centroidIndices);
        }}
    }}

    // Wire up zone pill button clicks
    document.addEventListener('DOMContentLoaded', function() {{
        const zonePills = document.querySelectorAll('.zone-pill');
        zonePills.forEach((btn, idx) => {{
            btn.addEventListener('click', function() {{
                navigateToZone(idx);
            }});
        }});

        // Wire up centroids toggle button
        // Find the button by its label text
        setTimeout(function() {{
            const buttons = document.querySelectorAll('.updatemenu-button');
            buttons.forEach(btn => {{
                if (btn.textContent.includes('Average Brake Points')) {{
                    btn.addEventListener('click', function(e) {{
                        e.preventDefault();
                        e.stopPropagation();
                        toggleCentroids();
                    }});
                }}
            }});
        }}, 500);  // Wait for Plotly to render

        // Wire up zone labels toggle button
        setTimeout(function() {{
            const plotDiv = document.querySelector('.plotly-graph-div');
            if (!plotDiv || !plotDiv.data) return;

            // Find all zone-badge traces by meta attribute
            const zoneBadgeIndices = plotDiv.data
                .map((t, i) => (t && t.meta === 'zone-badge' ? i : -1))
                .filter(i => i >= 0);

            if (zoneBadgeIndices.length === 0) return;

            // Track zone labels visibility state
            let zoneLabelsVisible = false;

            // Find and wire up the Zone Labels button
            const buttons = document.querySelectorAll('.updatemenu-button');
            buttons.forEach(btn => {{
                if (btn.textContent.includes('Zone Labels')) {{
                    btn.addEventListener('click', function(e) {{
                        e.preventDefault();
                        e.stopPropagation();

                        // Toggle visibility state
                        zoneLabelsVisible = !zoneLabelsVisible;

                        // Update all zone-badge traces
                        Plotly.restyle(plotDiv, {{'visible': zoneLabelsVisible}}, zoneBadgeIndices);
                    }});
                }}
            }});
        }}, 500);  // Wait for Plotly to render
    }});

    // Keyboard navigation with smooth zoom transitions
    document.addEventListener('keydown', function(e) {{
        // Don't interfere with input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {{
            return;
        }}

        // Prevent animation queueing when users spam keys
        if (isAnimating) {{
            return;
        }}

        const maxIndex = ZONE_DATA.length - 1;
        let newIndex = activeZoneIndex;

        // Arrow key navigation
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {{
            newIndex = (activeZoneIndex + 1) % (maxIndex + 1);  // Wrap around
            e.preventDefault();
        }} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{
            newIndex = (activeZoneIndex - 1 + maxIndex + 1) % (maxIndex + 1);  // Wrap around
            e.preventDefault();
        }} else {{
            return;  // Not an arrow key
        }}

        if (newIndex !== activeZoneIndex) {{
            navigateToZone(newIndex);
        }}
    }});

    // Link centroid visibility to driver legend toggles
    document.addEventListener('DOMContentLoaded', function() {{
        const plotDiv = document.querySelector('.plotly-graph-div');
        if (!plotDiv) return;

        // Intercept legend clicks when in centroid mode
        plotDiv.on('plotly_legendclick', function(data) {{
            if (displayMode !== 'centroids') return true; // Allow default in points mode

            const clickedTraceIndex = data.curveNumber;

            // Check if this is a driver brake trace
            if (clickedTraceIndex < FIRST_DRIVER_IDX || clickedTraceIndex >= FIRST_DRIVER_IDX + NUM_DRIVERS) {{
                return true; // Not a driver trace, allow default
            }}

            const driverOffset = clickedTraceIndex - FIRST_DRIVER_IDX;
            const centroidIdx = FIRST_CENTROID_IDX + driverOffset;
            const currentTrace = plotDiv.data[clickedTraceIndex];

            // Toggle visible state
            const newVisible = currentTrace.visible === true ? 'legendonly' : true;

            // Update brake trace (for legend state) and centroid trace
            Plotly.restyle(plotDiv, {{'visible': newVisible}}, [clickedTraceIndex]);
            Plotly.restyle(plotDiv, {{
                'visible': newVisible,
                'marker.opacity': newVisible === true ? 1 : 0
            }}, [centroidIdx]);

            return false; // Prevent default
        }});
    }});
    </script>
    """

    # Inject wrapper structure around Plotly div
    import re

    # Find the plotly-graph-div and wrap it with toolbar + wrapper
    plotly_div_pattern = r'(<div[^>]*class="plotly-graph-div"[^>]*>.*?</script>)'

    def wrap_with_toolbar(match):
        return f'<div id="plot-wrapper">\n{toolbar_html}\n{match.group(1)}\n</div>'

    html_content = re.sub(
        plotly_div_pattern, wrap_with_toolbar, html_content, flags=re.DOTALL
    )

    # Insert CSS into head and script before closing </body>
    html_content = html_content.replace("</head>", fullscreen_css + "\n</head>")
    html_content = html_content.replace("</body>", keyboard_script + "\n</body>")
    output_path.write_text(html_content)

    print(f"✓ Saved zone-focused dashboard to: {output_path}")
    print("✓ Added external zone pill toolbar (prevents click-blocking)")
    print("✓ Added keyboard navigation (arrow keys to cycle zones)")
    print("✓ Added smooth zoom animations (500ms cubic-easing)")
    print("✓ Added hover tooltips (shows coordinates on brake points)")
    print("✓ Added UI state persistence (zoom/pan preserved across legend toggles)")
    print()

    return fig


def render_zone_focus_dashboard(
    telemetry_df,
    brake_events_df,
    driver_summary_df,
    centroids_df,
    reference_vehicle_number,
    output_path,
    centerline_csv_path=None,
    corner_definitions_json=None,
    corner_labels_json=None,
    pit_lane_json=None,
):
    """
    Wrapper for create_zone_focused_dashboard matching main.py's interface.

    Note: corner_definitions_json and pit_lane_json are accepted but unused
    (zone bounds are computed from data, pit lane not currently rendered).

    Args:
        telemetry_df: Full telemetry DataFrame for track rendering
        brake_events_df: Brake events DataFrame
        driver_summary_df: Driver summary with lap times
        centroids_df: Zone centroids DataFrame (average brake points per driver per zone)
        reference_vehicle_number: Vehicle number of reference driver
        output_path: Path to save HTML file
        centerline_csv_path: Path to centerline CSV (optional, loads if exists)
        corner_definitions_json: Path to corner definitions JSON (unused)
        corner_labels_json: Path to corner labels JSON
        pit_lane_json: Path to pit lane JSON (unused)

    Returns:
        Plotly figure object
    """
    return create_zone_focused_dashboard(
        telemetry_df=telemetry_df,
        brake_events_df=brake_events_df,
        driver_summary_df=driver_summary_df,
        centroids_df=centroids_df,
        reference_vehicle_number=reference_vehicle_number,
        output_path=output_path,
        centerline_path=centerline_csv_path,
        corner_labels_json=corner_labels_json,
    )
