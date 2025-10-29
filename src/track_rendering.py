# ABOUTME: Generate track outline visualization from GPS data
# ABOUTME: Handles GPS smoothing and track plotting with Plotly

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from pathlib import Path
from shapely.geometry import LineString, Polygon
from scipy.spatial import cKDTree


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
    Compute unit tangents and normals along a polyline.

    Returns:
        t_hat (N,2), n_hat (N,2)
    """
    dx = np.gradient(x)
    dy = np.gradient(y)
    mag = np.hypot(dx, dy)
    mag[mag == 0] = 1.0
    tx = dx / mag
    ty = dy / mag
    # Rotate tangent 90° CCW to get normal
    nx = -ty
    ny = tx
    t_hat = np.column_stack([tx, ty])
    n_hat = np.column_stack([nx, ny])
    return t_hat, n_hat


def build_data_driven_band(
    telemetry_df,
    x_center,
    y_center,
    sample_fraction=0.25,
    q_high=0.90,
    min_width=6.0,
    max_width=16.0,
):
    """
    Build a meter-true track band (donut) using data-driven half-widths
    derived from signed cross-track offsets of telemetry positions.

    Args:
        telemetry_df: DataFrame with x_meters, y_meters (and optional speed)
        x_center, y_center: centerline arrays WITHOUT duplicate closing point
        sample_fraction: fraction of telemetry points to sample for speed
        q_high: high quantile used for half-width estimation per side
        min_width, max_width: clamps for total width in meters

    Returns:
        (x_left, y_left, x_right, y_right, stats)
    """
    # Prepare centerline and normals
    x_c = np.asarray(x_center)
    y_c = np.asarray(y_center)
    n_stations = len(x_c)
    _, n_hat = _compute_normals(x_c, y_c)

    # KD-tree for nearest station
    tree = cKDTree(np.column_stack([x_c, y_c]))

    # Sample telemetry for efficiency
    df_pos = telemetry_df[["x_meters", "y_meters", "speed"]].copy() if "speed" in telemetry_df.columns else telemetry_df[["x_meters", "y_meters"]].copy()
    df_pos = df_pos.dropna(subset=["x_meters", "y_meters"]).sample(frac=sample_fraction, random_state=42)

    # Optional: basic speed gate to reduce pit/garage noise
    if "speed" in df_pos.columns:
        df_pos["speed"] = pd.to_numeric(df_pos["speed"], errors="coerce")
        df_pos = df_pos[df_pos["speed"].fillna(100) > 30]

    pts = df_pos[["x_meters", "y_meters"]].to_numpy()
    dists, idxs = tree.query(pts, k=1)

    # Vector from centerline to point
    vc = pts - np.column_stack([x_c[idxs], y_c[idxs]])
    # Signed offset using local normal
    d_signed = np.einsum("ij,ij->i", vc, n_hat[idxs])

    # Aggregate by station index
    df_proj = pd.DataFrame({"idx": idxs, "d": d_signed})

    # Positive offsets (left), negative (right)
    left_q = df_proj[df_proj["d"] > 0].groupby("idx")["d"].quantile(q_high)
    right_q = (-df_proj[df_proj["d"] < 0]["d"]).groupby(idxs[df_proj["d"] < 0]).quantile(q_high)

    # Initialize widths
    wL = np.full(n_stations, np.nan)
    wR = np.full(n_stations, np.nan)
    wL[left_q.index.values] = left_q.values
    wR[right_q.index.values] = right_q.values

    # Fill gaps by nearest neighbor then forward/backward fill
    def _fill_nan(a):
        s = pd.Series(a)
        s = s.interpolate(limit_direction="both")
        # If still NaN (all-NaN series), default to median later
        return s.to_numpy()

    wL = _fill_nan(wL)
    wR = _fill_nan(wR)

    # If arrays are still NaN entirely, set defaults
    if np.all(np.isnan(wL)):
        wL[:] = min_width / 2
    if np.all(np.isnan(wR)):
        wR[:] = min_width / 2

    # Total width and clamps
    total_w = wL + wR
    # Replace any remaining NaNs with median
    if np.any(np.isnan(total_w)):
        med = np.nanmedian(total_w)
        total_w[np.isnan(total_w)] = med if not np.isnan(med) else (min_width + max_width) / 2
    total_w = np.clip(total_w, min_width, max_width)

    # Balance sides proportionally where one side is missing
    # Keep original ratios where available; otherwise split evenly
    ratio = np.divide(wL, wL + wR, out=np.full_like(wL, 0.5, dtype=float), where=(wL + wR) != 0)
    wL = ratio * total_w
    wR = (1 - ratio) * total_w

    # Smooth half-widths along stations
    window = min(51, (len(total_w) // 3) | 1)
    try:
        wL_s = savgol_filter(wL, window, 3, mode="nearest")
        wR_s = savgol_filter(wR, window, 3, mode="nearest")
    except Exception:
        wL_s, wR_s = wL, wR

    # Build edges
    x_left = x_c + wL_s * n_hat[:, 0]
    y_left = y_c + wL_s * n_hat[:, 1]
    x_right = x_c - wR_s * n_hat[:, 0]
    y_right = y_c - wR_s * n_hat[:, 1]

    stats = {
        "width_p05": float(np.percentile(total_w, 5)),
        "width_p50": float(np.percentile(total_w, 50)),
        "width_p95": float(np.percentile(total_w, 95)),
        "min_width": float(np.min(total_w)),
        "max_width": float(np.max(total_w)),
        "stations": int(n_stations),
        "samples_used": int(len(df_pos)),
    }

    return x_left, y_left, x_right, y_right, stats


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

    # Data-driven donut band (annulus) from all telemetry positions
    # Single source of truth: load if saved, else compute and save
    base_dir = Path(__file__).parent.parent
    band_path = base_dir / "data" / "gps-tracks" / "track_band.csv"
    if band_path.exists():
        print(f"  Loading precomputed track band: {band_path}")
        x_left, y_left, x_right, y_right = load_track_band(band_path)
        # Stats will be computed from polygon below
        wstats = None
    else:
        print("  Computing track band from telemetry (first run)...")
        x_left, y_left, x_right, y_right, wstats = build_data_driven_band(
            telemetry_df, x_smooth[:-1], y_smooth[:-1]
        )
        save_track_band(x_left, y_left, x_right, y_right, band_path)
        print(f"  ✓ Saved track band to: {band_path}")

    # Build polygon ring: left edge forward, right edge reversed
    x_ring = np.concatenate([x_left, x_right[::-1], [x_left[0]]])
    y_ring = np.concatenate([y_left, y_right[::-1], [y_left[0]]])

    # Validation logs using polygon area
    track_length_m = float(distances[-1]) if 'distances' in locals() else np.nan
    poly = Polygon(np.column_stack([x_ring, y_ring]))
    surface_area = float(poly.area)
    implied_width = surface_area / track_length_m if track_length_m == track_length_m else np.nan
    print(f"  Track surface area: {surface_area:.0f} m^2")
    if track_length_m == track_length_m:
        print(f"  Implied avg width: {implied_width:.1f} m" + (f" (p50 {wstats['width_p50']:.1f} m)" if wstats else ""))
    if wstats:
        print(
            f"  Width stats (m): p05 {wstats['width_p05']:.1f}, p50 {wstats['width_p50']:.1f}, p95 {wstats['width_p95']:.1f}"
        )

    # Plot donut band
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
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(gridcolor="#333333", showgrid=True, zeroline=False),
        hovermode="closest",
        showlegend=True,
        width=1200,
        height=800,
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


def save_track_band(x_left, y_left, x_right, y_right, output_path):
    """
    Save track band edges to CSV as single table with columns:
    left_x,left_y,right_x,right_y per station index.
    """
    df = pd.DataFrame(
        {
            "left_x": np.asarray(x_left),
            "left_y": np.asarray(y_left),
            "right_x": np.asarray(x_right),
            "right_y": np.asarray(y_right),
        }
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def load_track_band(input_path):
    """
    Load track band edges from CSV saved by save_track_band().

    Returns: x_left, y_left, x_right, y_right (numpy arrays)
    """
    df = pd.read_csv(input_path)
    return (
        df["left_x"].to_numpy(),
        df["left_y"].to_numpy(),
        df["right_x"].to_numpy(),
        df["right_y"].to_numpy(),
    )
