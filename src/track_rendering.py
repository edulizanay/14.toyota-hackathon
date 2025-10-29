# ABOUTME: Generate track outline visualization from GPS data
# ABOUTME: Handles GPS smoothing and track plotting with Plotly

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import UnivariateSpline
from shapely.geometry import LineString
from pathlib import Path


def build_track_surface(centerline_xy, width_m=12.0):
    """
    Create track surface polygon by buffering the centerline.

    Args:
        centerline_xy: List of (x, y) tuples representing centerline in meters
        width_m: Total track width in meters (default: 12.0)

    Returns:
        tuple: (poly_x, poly_y) - polygon coordinates for plotting
    """
    half = width_m / 2.0
    line = LineString(centerline_xy)
    poly = line.buffer(half, cap_style=1, join_style=1)  # round caps/joins
    poly = poly.simplify(tolerance=1.0)  # remove spiky vertices
    ext = poly.exterior
    return list(ext.coords.xy[0]), list(ext.coords.xy[1])


def generate_track_outline(
    telemetry_df, vehicle_number=None, lap_number=None, smoothing=0.001
):
    """
    Generate track outline from GPS coordinates.

    Args:
        telemetry_df: DataFrame with GPS coordinates (x_meters, y_meters)
        vehicle_number: Specific vehicle to use (default: fastest driver)
        lap_number: Specific lap to use (default: best lap for vehicle)
        smoothing: Smoothing parameter for UnivariateSpline (default: 0.001)

    Returns:
        tuple: (smoothed_x, smoothed_y, fig) - smoothed coordinates and Plotly figure
    """
    # If no vehicle specified, use fastest driver from the data
    if vehicle_number is None:
        # Use first vehicle with data as default (we'll identify fastest later)
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

    # Close the loop by adding first point at end
    x = np.append(x, x[0])
    y = np.append(y, y[0])

    # Apply smoothing with UnivariateSpline
    print(f"Applying smoothing (s={smoothing})...")

    # Create parameter t (0 to 1) for spline
    t = np.linspace(0, 1, len(x))

    # Fit splines for x and y separately
    try:
        spline_x = UnivariateSpline(t, x, s=smoothing * len(x), k=3)
        spline_y = UnivariateSpline(t, y, s=smoothing * len(y), k=3)

        # Generate smooth points
        t_smooth = np.linspace(0, 1, len(x) * 2)  # 2x points for smoother line
        x_smooth = spline_x(t_smooth)
        y_smooth = spline_y(t_smooth)

        print(f"Smoothed to {len(x_smooth)} points")
    except Exception as e:
        print(f"Warning: Smoothing failed ({e}), using raw points")
        x_smooth = x
        y_smooth = y

    # Build track surface polygon (12m width)
    print("Building track surface polygon (12m width)...")
    centerline_xy = list(zip(x_smooth, y_smooth))
    poly_x, poly_y = build_track_surface(centerline_xy, width_m=12.0)

    # Create Plotly figure with dark theme
    fig = go.Figure()

    # Add track surface (filled polygon, behind everything)
    fig.add_trace(
        go.Scatter(
            x=poly_x,
            y=poly_y,
            mode="lines",
            fill="toself",
            fillcolor="rgba(255,255,255,0.07)",
            line=dict(color="rgba(220,220,220,0.2)", width=1),
            name="Track surface",
            hoverinfo="skip",
        )
    )

    # Add centerline (on top of surface)
    fig.add_trace(
        go.Scatter(
            x=x_smooth,
            y=y_smooth,
            mode="lines",
            line=dict(color="#5cf", width=3),
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
