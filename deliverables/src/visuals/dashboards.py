# ABOUTME: Interactive Plotly dashboards for brake point analysis and zone comparison
# ABOUTME: Zone-focused view with pills, toggles, rotation, and keyboard navigation

import json
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


def create_zone_focused_dashboard(
    telemetry_df,
    brake_events_df,
    driver_summary_df,
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
    print()

    # 2) Compute zone bboxes
    print("Computing zone boundaries...")
    zone_bounds = compute_zone_bounds(brake_events_df, padding_m=20.0)
    zone_order = sorted(zone_bounds.keys())
    print(f"✓ Calculated boundaries for {len(zone_order)} zones")
    print()

    # 3) Get reference brake events
    ref_brakes = brake_events_df[
        (brake_events_df["vehicle_number"] == reference_vehicle_number)
        & (brake_events_df["zone_id"].notna())
    ].copy()

    # 4) Corner labels (1-17)
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

    # 5) Reference trace (white, all zones)
    print("Adding reference driver brake points...")
    fig.add_trace(
        go.Scatter(
            x=ref_brakes["x_meters"],
            y=ref_brakes["y_meters"],
            mode="markers",
            marker=dict(size=8, color="rgba(255,255,255,0.6)"),
            name=f"Winner (#{reference_vehicle_number})",
            hovertemplate="Ref x: %{x:.1f}m<br>y: %{y:.1f}m<extra></extra>",
            visible=True,
        )
    )
    print(f"✓ Added {len(ref_brakes)} reference brake points (white)")
    print()

    # 6) One comparison trace per driver (all zones), colored by driver
    print("Preparing comparison driver traces...")
    valid = driver_summary_df.dropna(subset=["fastest_lap_seconds"]).sort_values(
        "fastest_lap_seconds"
    )
    driver_list = [
        int(v)
        for v in valid["vehicle_number"].tolist()
        if int(v) != reference_vehicle_number
    ]

    for drv in driver_list:
        df_drv = brake_events_df[
            (brake_events_df["vehicle_number"] == drv)
            & (brake_events_df["zone_id"].notna())
        ].copy()
        driver_color = DRIVER_COLORS.get(drv, "#999")
        fig.add_trace(
            go.Scatter(
                x=df_drv["x_meters"],
                y=df_drv["y_meters"],
                mode="markers",
                marker=dict(
                    size=10,
                    color=driver_color,
                    line=dict(color="rgba(255,255,255,0.7)", width=2),
                ),
                name=f"#{drv} ({valid[valid['vehicle_number'] == drv].iloc[0]['fastest_lap_time']})",
                hovertemplate=f"#{drv} x: %{{x:.1f}}m<br>y: %{{y:.1f}}m<extra></extra>",
                visible="legendonly",  # hidden by default, but toggleable via legend
                showlegend=True,
            )
        )
    print(f"✓ Added traces for {len(driver_list)} drivers")
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

    # 8) Corner labels and axes toggle buttons
    print("Creating toggle buttons for labels...")
    # Find trace indices
    base_trace_count = len(fig.data) - len(driver_list)
    corner_labels_idx = (
        base_trace_count - 2
    )  # Corner labels is 2 traces before drivers (ref is -1)

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
    print("✓ Created corner labels toggle button")
    print("✓ Created axes toggle button")
    print()

    # 9) Layout: add toggles (zone pills moved to external toolbar), use legend for drivers
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
            corner_toggle_button,
            axes_toggle_button,
        ],
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

    // Current active zone index
    let activeZoneIndex = 0;

    // Animation state tracking to prevent queueing
    let isAnimating = false;

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

    // Wire up zone pill button clicks
    document.addEventListener('DOMContentLoaded', function() {{
        const zonePills = document.querySelectorAll('.zone-pill');
        zonePills.forEach((btn, idx) => {{
            btn.addEventListener('click', function() {{
                navigateToZone(idx);
            }});
        }});
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
        reference_vehicle_number=reference_vehicle_number,
        output_path=output_path,
        centerline_path=centerline_csv_path,
        corner_labels_json=corner_labels_json,
    )
