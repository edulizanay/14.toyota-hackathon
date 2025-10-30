# ABOUTME: Generate track outline visualization from GPS data
# ABOUTME: Handles GPS smoothing and track plotting with Plotly

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from pathlib import Path


def resample_by_distance(x, y, step_m=2.0, spike_threshold_m=10.0):
    """
    Resample GPS track to uniform distance spacing, removing spikes.

    Args:
        x: x coordinates in meters
        y: y coordinates in meters
        step_m: Target spacing between points in meters
        spike_threshold_m: Maximum allowed segment length (drop spikes exceeding this)

    Returns:
        tuple: (x_resampled, y_resampled, distances)
    """
    # Compute segment distances
    dx = np.diff(x)
    dy = np.diff(y)
    segment_dist = np.sqrt(dx**2 + dy**2)

    # Remove spikes (segments longer than threshold)
    spike_mask = segment_dist > spike_threshold_m
    if np.any(spike_mask):
        spike_indices = np.where(spike_mask)[0]
        print(f"  Removing {len(spike_indices)} spikes (>{spike_threshold_m}m)")

        # Keep only non-spike segments
        keep_mask = np.ones(len(x), dtype=bool)
        keep_mask[spike_indices + 1] = False  # Remove the point after the spike
        x = x[keep_mask]
        y = y[keep_mask]

        # Recalculate distances
        dx = np.diff(x)
        dy = np.diff(y)
        segment_dist = np.sqrt(dx**2 + dy**2)

    # Remove duplicates (zero distance)
    duplicate_mask = segment_dist < 1e-6
    if np.any(duplicate_mask):
        dup_indices = np.where(duplicate_mask)[0]
        print(f"  Removing {len(dup_indices)} duplicate points")

        keep_mask = np.ones(len(x), dtype=bool)
        keep_mask[dup_indices + 1] = False
        x = x[keep_mask]
        y = y[keep_mask]

        # Recalculate distances
        dx = np.diff(x)
        dy = np.diff(y)
        segment_dist = np.sqrt(dx**2 + dy**2)

    # Compute cumulative distance
    cumulative_dist = np.concatenate([[0], np.cumsum(segment_dist)])
    total_distance = cumulative_dist[-1]

    print(f"  Total track length: {total_distance:.1f}m")
    print(f"  Original points: {len(x)}")

    # Create uniform distance stations
    num_stations = int(np.ceil(total_distance / step_m)) + 1
    uniform_dist = np.linspace(0, total_distance, num_stations)

    # Interpolate x and y at uniform distances
    interp_x = interp1d(
        cumulative_dist, x, kind="linear", bounds_error=False, fill_value="extrapolate"
    )
    interp_y = interp1d(
        cumulative_dist, y, kind="linear", bounds_error=False, fill_value="extrapolate"
    )

    x_resampled = interp_x(uniform_dist)
    y_resampled = interp_y(uniform_dist)

    print(f"  Resampled to {len(x_resampled)} points (step={step_m}m)")

    return x_resampled, y_resampled, uniform_dist


def smooth_periodic(x, y, window_length=31, polyorder=3, wrap_count=25):
    """
    Apply Savitzky-Golay smoothing with periodic wrapping to avoid endpoint kink.

    Args:
        x: x coordinates
        y: y coordinates
        window_length: Smoothing window size (must be odd)
        polyorder: Polynomial order for Savitzky-Golay
        wrap_count: Number of points to wrap from each end

    Returns:
        tuple: (x_smooth, y_smooth)
    """
    if window_length % 2 == 0:
        window_length += 1  # Must be odd

    if window_length >= len(x):
        print(
            f"  Warning: Window ({window_length}) >= points ({len(x)}), reducing to {len(x) // 3 | 1}"
        )
        window_length = (len(x) // 3) | 1  # Make odd
        if window_length < 5:
            print("  Warning: Too few points for smoothing, skipping")
            return x, y

    # Wrap points for periodic smoothing
    x_wrapped = np.concatenate([x[-wrap_count:], x, x[:wrap_count]])
    y_wrapped = np.concatenate([y[-wrap_count:], y, y[:wrap_count]])

    # Apply Savitzky-Golay filter
    x_smooth_wrapped = savgol_filter(
        x_wrapped, window_length, polyorder, mode="nearest"
    )
    y_smooth_wrapped = savgol_filter(
        y_wrapped, window_length, polyorder, mode="nearest"
    )

    # Extract the middle (unwrap)
    x_smooth = x_smooth_wrapped[wrap_count:-wrap_count]
    y_smooth = y_smooth_wrapped[wrap_count:-wrap_count]

    print(f"  Applied Savitzky-Golay (window={window_length}, poly={polyorder})")

    return x_smooth, y_smooth


def _compute_normals(x, y):
    """
    Compute unit normals along a polyline defined by (x, y).
    Returns array of shape (N, 2) for normals.
    """
    dx = np.gradient(x)
    dy = np.gradient(y)
    mag = np.hypot(dx, dy)
    mag[mag == 0] = 1.0
    tx = dx / mag
    ty = dy / mag
    # Rotate tangent 90° CCW → normal
    nx = -ty
    ny = tx
    return np.column_stack([nx, ny])


def generate_track_outline(
    telemetry_df,
    vehicle_number=None,
    lap_number=None,
    resample_step_m=2.0,
    spike_threshold_m=10.0,
    savgol_window=31,
    savgol_poly=3,
    wrap_count=25,
):
    """
    Generate track outline from GPS coordinates with distance-based smoothing.

    Args:
        telemetry_df: DataFrame with GPS coordinates (x_meters, y_meters)
        vehicle_number: Specific vehicle to use (default: fastest driver)
        lap_number: Specific lap to use (default: best lap for vehicle)
        resample_step_m: Target spacing for resampling in meters (default: 2.0)
        spike_threshold_m: Maximum segment length before considering it a spike (default: 10.0)
        savgol_window: Savitzky-Golay window size (default: 31)
        savgol_poly: Savitzky-Golay polynomial order (default: 3)
        wrap_count: Points to wrap for periodic smoothing (default: 25)

    Returns:
        tuple: (smoothed_x, smoothed_y, fig) - smoothed coordinates and Plotly figure
    """
    # If no vehicle specified, use fastest driver from the data
    if vehicle_number is None:
        vehicle_number = telemetry_df["vehicle_number"].iloc[0]
        print(f"Using vehicle #{vehicle_number}")

    # Filter to specific vehicle
    vehicle_data = telemetry_df[telemetry_df["vehicle_number"] == vehicle_number].copy()

    # If no lap specified, find lap with most complete GPS data
    if lap_number is None:
        lap_counts = vehicle_data.groupby("lap").size()
        lap_number = lap_counts.idxmax()
        print(f"Using lap #{lap_number} (most complete GPS data)")

    # Get lap data
    lap_data = vehicle_data[vehicle_data["lap"] == lap_number].copy()

    # Sort by timestamp to ensure correct order
    lap_data = lap_data.sort_values("timestamp")

    print(f"Track outline points: {len(lap_data)}")

    # Extract coordinates
    x = lap_data["x_meters"].values
    y = lap_data["y_meters"].values

    # Phase 1: Resample by distance
    print("\nPhase 1: Distance-based resampling")
    x_resampled, y_resampled, distances = resample_by_distance(
        x, y, step_m=resample_step_m, spike_threshold_m=spike_threshold_m
    )

    # Phase 2: Smooth with periodic wrapping
    print("\nPhase 2: Periodic smoothing")
    x_smooth, y_smooth = smooth_periodic(
        x_resampled,
        y_resampled,
        window_length=savgol_window,
        polyorder=savgol_poly,
        wrap_count=wrap_count,
    )

    # Close the loop for visualization (add first point at end)
    x_smooth = np.append(x_smooth, x_smooth[0])
    y_smooth = np.append(y_smooth, y_smooth[0])

    print(f"\n✓ Final smoothed track: {len(x_smooth)} points")

    # Create Plotly figure with dark theme
    fig = go.Figure()

    # Ensure consistent centerline across pages: load if saved
    base_dir = Path(__file__).parent.parent
    center_path = base_dir / "data" / "gps-tracks" / "track_centerline.csv"
    if center_path.exists():
        df_center = pd.read_csv(center_path)
        x_c = df_center["x_meters"].to_numpy()
        y_c = df_center["y_meters"].to_numpy()
        # Replace smoothed arrays with persisted centerline
        x_smooth = np.append(x_c, x_c[0])
        y_smooth = np.append(y_c, y_c[0])
        print(f"  Loaded centerline: {center_path}")
    else:
        # Save newly computed centerline for reuse
        save_track_data(x_smooth, y_smooth, center_path)

    # Meter-true fixed-width donut built from centerline normals (outer + inner ring)
    track_width_m = 18.0  # total width in meters (widened by +2m more)
    half_width = track_width_m / 2.0
    x_c = x_smooth[:-1]
    y_c = y_smooth[:-1]
    n_hat = _compute_normals(x_c, y_c)
    # Left/outer and right/inner edges (order does not matter for ring if we reverse one side)
    x_left = x_c + half_width * n_hat[:, 0]
    y_left = y_c + half_width * n_hat[:, 1]
    x_right = x_c - half_width * n_hat[:, 0]
    y_right = y_c - half_width * n_hat[:, 1]
    # Build ring path: left forward, right reversed, and close
    x_ring = np.concatenate([x_left, x_right[::-1], [x_left[0]]])
    y_ring = np.concatenate([y_left, y_right[::-1], [y_left[0]]])
    fig.add_trace(
        go.Scatter(
            x=x_ring,
            y=y_ring,
            mode="lines",
            fill="toself",
            line=dict(color="rgba(100,100,100,0.35)", width=1),
            fillcolor="rgba(255,255,255,0.07)",
            name="Track surface",
            hoverinfo="skip",
        )
    )

    # Thin cyan centerline (crisp reference line)
    fig.add_trace(
        go.Scatter(
            x=x_smooth,
            y=y_smooth,
            mode="lines",
            line=dict(color="#5cf", width=2),
            name="Centerline",
            hovertemplate="x: %{x:.1f}m<br>y: %{y:.1f}m<extra></extra>",
        )
    )

    # Update layout with dark theme
    fig.update_layout(
        title=f"Barber Motorsports Park - Track Outline<br><sub>Vehicle #{vehicle_number}, Lap #{lap_number}</sub>",
        xaxis_title="X (meters)",
        yaxis_title="Y (meters)",
        plot_bgcolor="#0a0a0a",
        paper_bgcolor="#0a0a0a",
        font=dict(color="#ffffff", size=12),
        xaxis=dict(
            gridcolor="#333333",
            showgrid=True,
            zeroline=False,
            visible=False,
        ),
        yaxis=dict(gridcolor="#333333", showgrid=True, zeroline=False, visible=False),
        hovermode="closest",
        showlegend=True,
    )

    return x_smooth, y_smooth, fig


def save_track_data(x_smooth, y_smooth, output_path):
    """
    Save smoothed track centerline to CSV.

    Args:
        x_smooth: Smoothed x coordinates
        y_smooth: Smoothed y coordinates
        output_path: Path to save CSV
    """
    df_track = pd.DataFrame({"x_meters": x_smooth, "y_meters": y_smooth})

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_track.to_csv(output_path, index=False)

    print(f"✓ Saved track centerline to: {output_path}")

    # Note: band save/load utilities removed in rollback for simplicity
