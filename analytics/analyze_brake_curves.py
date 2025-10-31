# ABOUTME: Complete brake curve analysis - extracts, processes, and visualizes brake pressure curves
# ABOUTME: Compares podium (top 3) vs rest of field with phase-normalized averaging

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import timedelta
from scipy.interpolate import interp1d
import plotly.graph_objects as go

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent / "deliverables" / "src"))
from data_processing import load_and_pivot_telemetry

# Paths
ROOT_DIR = Path(__file__).parent.parent
DATA_INPUT = ROOT_DIR / "deliverables" / "data" / "input"
DATA_OUTPUT = ROOT_DIR / "deliverables" / "data" / "output"
ANALYTICS_OUTPUT = ROOT_DIR / "analytics"

# Configuration
TIME_WINDOW_BEFORE = 0.5
TIME_WINDOW_AFTER = 7.0
RELEASE_PRESSURE_THRESHOLD = 0.5
RELEASE_PADDING = 0.5
SPLIT_TIME = 2.0  # Split Zone 4 and 6 at 2 seconds
NORMALIZED_POINTS = 200  # Points in phase-normalized grid


def load_data():
    """Load brake events, telemetry, and identify podium drivers."""
    print("=" * 80)
    print("LOADING DATA")
    print("=" * 80)

    # Load USAC for podium identification
    usac = pd.read_csv(DATA_INPUT / "usac.csv", sep=";")
    podium_cars = set(usac.sort_values("POSITION").head(3)["NUMBER"].values)
    print(f"\nPodium drivers: {sorted(podium_cars)}")

    # Load brake events
    brake_events = pd.read_csv(DATA_OUTPUT / "brake_events.csv")
    brake_events = brake_events[brake_events["zone_id"].notna()].copy()
    print(f"Brake events: {len(brake_events):,}")

    # Load telemetry
    telemetry = load_and_pivot_telemetry(DATA_INPUT / "telemetry.csv")
    telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"])
    brake_events["timestamp"] = pd.to_datetime(brake_events["timestamp"])
    telemetry = telemetry.sort_values(["vehicle_number", "timestamp"])

    return brake_events, telemetry, podium_cars


def calculate_brake_threshold(telemetry):
    """Calculate brake pressure threshold (5th percentile)."""
    all_brake_f = telemetry["pbrake_f"].fillna(0)
    all_brake_r = telemetry["pbrake_r"].fillna(0)
    positive_pressures = np.concatenate(
        [all_brake_f[all_brake_f > 0].values, all_brake_r[all_brake_r > 0].values]
    )
    threshold = np.percentile(positive_pressures, 5)
    print(f"\nBrake threshold: {threshold:.2f} bar")
    return threshold


def extract_brake_curve(brake_event, telemetry, threshold):
    """Extract complete brake pressure curve for a single event."""
    vehicle_num = brake_event["vehicle_number"]
    onset_time = brake_event["timestamp"]

    vehicle_telemetry = telemetry[telemetry["vehicle_number"] == vehicle_num].copy()

    start_time = onset_time - timedelta(seconds=TIME_WINDOW_BEFORE)
    end_time = onset_time + timedelta(seconds=TIME_WINDOW_AFTER)

    window = vehicle_telemetry[
        (vehicle_telemetry["timestamp"] >= start_time)
        & (vehicle_telemetry["timestamp"] <= end_time)
    ].copy()

    if len(window) < 5:
        return None

    window["pressure"] = window[["pbrake_f", "pbrake_r"]].max(axis=1).fillna(0)
    window["time_offset"] = (window["timestamp"] - onset_time).dt.total_seconds()

    # Find release point (pressure drops to near zero after peak)
    after_onset = window[window["time_offset"] >= 0]
    if len(after_onset) == 0:
        return None

    peak_idx = after_onset["pressure"].idxmax()
    after_peak = window.loc[peak_idx:]
    release_idx = after_peak[after_peak["pressure"] < RELEASE_PRESSURE_THRESHOLD].index

    if len(release_idx) > 0:
        release_time = window.loc[release_idx[0], "time_offset"]
        window = window[window["time_offset"] <= release_time + RELEASE_PADDING]

    duration = window["time_offset"].max() - window["time_offset"].min()
    if duration < 0.2 or duration > 10.0:
        return None

    return window[["time_offset", "pressure"]].copy()


def extract_all_curves(brake_events, telemetry, threshold):
    """Extract curves for all brake events."""
    print("\n" + "=" * 80)
    print("EXTRACTING BRAKE CURVES")
    print("=" * 80)

    curves = []
    for idx, event in brake_events.iterrows():
        if idx % 500 == 0:
            print(f"Processing {idx + 1}/{len(brake_events)}...")

        curve = extract_brake_curve(event, telemetry, threshold)
        if curve is not None:
            curve["vehicle_number"] = event["vehicle_number"]
            curve["zone_id"] = event["zone_id"]
            curves.append(curve)

    print(
        f"\nExtracted {len(curves)}/{len(brake_events)} curves ({len(curves) / len(brake_events) * 100:.1f}%)"
    )
    return curves


def average_curves_per_driver_per_zone(curves):
    """Average all curves for each driver in each zone."""
    print("\n" + "=" * 80)
    print("AVERAGING PER DRIVER PER ZONE")
    print("=" * 80)

    driver_zone_curves = {}

    for (vehicle_num, zone_id), group in pd.DataFrame(
        [
            {
                "vehicle_number": c["vehicle_number"].iloc[0],
                "zone_id": c["zone_id"].iloc[0],
                "curve": c,
            }
            for c in curves
        ]
    ).groupby(["vehicle_number", "zone_id"]):
        # Interpolate all curves to uniform time grid
        interpolated = []
        for _, row in group.iterrows():
            curve = row["curve"]
            t = curve["time_offset"].values
            p = curve["pressure"].values

            if len(t) < 2:
                continue

            t_uniform = np.arange(t.min(), t.max(), 0.05)
            interp_func = interp1d(
                t, p, kind="linear", bounds_error=False, fill_value=0
            )
            p_uniform = interp_func(t_uniform)

            interpolated.append(
                pd.DataFrame({"time_offset": t_uniform, "pressure": p_uniform})
            )

        if len(interpolated) == 0:
            continue

        # Find common time range (maximum to capture full curves)
        time_min = min([c["time_offset"].min() for c in interpolated])
        time_max = max([c["time_offset"].max() for c in interpolated])
        common_time = np.arange(time_min, time_max, 0.05)

        # Average pressure at each time point
        all_pressures = []
        for curve in interpolated:
            interp_func = interp1d(
                curve["time_offset"].values,
                curve["pressure"].values,
                kind="linear",
                bounds_error=False,
                fill_value=0,
            )
            all_pressures.append(interp_func(common_time))

        avg_pressure = np.mean(all_pressures, axis=0)

        driver_zone_curves[(vehicle_num, zone_id)] = pd.DataFrame(
            {"time_offset": common_time, "pressure": avg_pressure}
        )

    print(f"Averaged {len(driver_zone_curves)} driver-zone combinations")
    return driver_zone_curves


def split_double_zones(driver_zone_curves):
    """Split Zone 4 and 6 at t=2s into separate zones."""
    print("\n" + "=" * 80)
    print("SPLITTING DOUBLE-PEAK ZONES")
    print("=" * 80)

    split_curves = {}

    for (vehicle_num, zone_id), curve in driver_zone_curves.items():
        if zone_id == 4:
            # Split Zone 4
            before = curve[curve["time_offset"] < SPLIT_TIME].copy()
            after = curve[curve["time_offset"] >= SPLIT_TIME].copy()

            if len(before) > 0:
                before["time_offset"] -= before["time_offset"].min()
                split_curves[(vehicle_num, 4)] = before

            if len(after) > 0:
                after["time_offset"] -= after["time_offset"].min()
                split_curves[(vehicle_num, 9)] = after

        elif zone_id == 6:
            # Split Zone 6
            before = curve[curve["time_offset"] < SPLIT_TIME].copy()
            after = curve[curve["time_offset"] >= SPLIT_TIME].copy()

            if len(before) > 0:
                before["time_offset"] -= before["time_offset"].min()
                split_curves[(vehicle_num, 6)] = before

            if len(after) > 0:
                after["time_offset"] -= after["time_offset"].min()
                split_curves[(vehicle_num, 10)] = after
        else:
            split_curves[(vehicle_num, zone_id)] = curve

    zones = set([z for _, z in split_curves.keys()])
    print(f"Split zones: {len(driver_zone_curves)} → {len(split_curves)} curves")
    print(f"Zones: {sorted(zones)}")

    return split_curves


def phase_normalize_and_average(driver_zone_curves, podium_cars):
    """Phase-normalize all curves and average podium vs rest."""
    print("\n" + "=" * 80)
    print("PHASE NORMALIZATION & AVERAGING")
    print("=" * 80)

    phase_grid = np.linspace(0, 100, NORMALIZED_POINTS)

    podium_curves = []
    rest_curves = []
    podium_durations = []
    rest_durations = []

    zones = set([zone_id for _, zone_id in driver_zone_curves.keys()])

    for zone_id in sorted(zones):
        # Get all driver curves for this zone
        zone_curves = {v: c for (v, z), c in driver_zone_curves.items() if z == zone_id}

        for vehicle_num, curve in zone_curves.items():
            if len(curve) < 3:
                continue

            # Normalize time to 0-100% phase
            t = curve["time_offset"].values
            p = curve["pressure"].values
            duration = t.max() - t.min()

            if duration <= 0:
                continue

            phase = ((t - t.min()) / duration) * 100

            # Interpolate to common phase grid
            interp_func = interp1d(
                phase, p, kind="linear", bounds_error=False, fill_value=(p[0], p[-1])
            )
            p_normalized = interp_func(phase_grid)
            p_normalized = np.clip(p_normalized, 0, None)

            # Add to appropriate group
            if vehicle_num in podium_cars:
                podium_curves.append(p_normalized)
                podium_durations.append(duration)
            else:
                rest_curves.append(p_normalized)
                rest_durations.append(duration)

    print(f"Normalized {len(podium_curves)} podium curves")
    print(f"Normalized {len(rest_curves)} rest curves")

    # Average across all zones
    podium_avg = np.mean(podium_curves, axis=0)
    rest_avg = np.mean(rest_curves, axis=0)

    avg_duration = np.mean(podium_durations + rest_durations)
    time_axis = (phase_grid / 100) * avg_duration

    # Convert to % of peak
    podium_peak = podium_avg.max()
    rest_peak = rest_avg.max()

    podium_pct = (podium_avg / podium_peak) * 100
    rest_pct = (rest_avg / rest_peak) * 100

    print(f"\nPodium peak: {podium_peak:.1f} bar")
    print(f"Rest peak: {rest_peak:.1f} bar")
    print(f"Average duration: {avg_duration:.2f}s")

    return {
        "time": time_axis,
        "phase": phase_grid,
        "podium_pct": podium_pct,
        "podium_pressure": podium_avg,
        "rest_pct": rest_pct,
        "rest_pressure": rest_avg,
        "podium_peak": podium_peak,
        "rest_peak": rest_peak,
    }


def create_visualization(data):
    """Create dark-themed visualization."""
    print("\n" + "=" * 80)
    print("CREATING VISUALIZATION")
    print("=" * 80)

    fig = go.Figure()

    # Podium line
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["podium_pct"],
            mode="lines",
            name="Winner",
            line=dict(color="#00cc00", width=5),
            hovertemplate=(
                "<b>Winner</b><br>"
                "Time: %{x:.2f}s<br>"
                "%% Peak: %{y:.1f}%%<br>"
                "Pressure: %{customdata:.1f} bar<extra></extra>"
            ),
            customdata=data["podium_pressure"],
        )
    )

    # Rest line
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["rest_pct"],
            mode="lines",
            name="Rest",
            line=dict(color="#ff4444", width=5),
            hovertemplate=(
                "<b>Rest</b><br>"
                "Time: %{x:.2f}s<br>"
                "%% Peak: %{y:.1f}%%<br>"
                "Pressure: %{customdata:.1f} bar<extra></extra>"
            ),
            customdata=data["rest_pressure"],
        )
    )

    # Brake onset line
    fig.add_vline(
        x=0,
        line_dash="dot",
        line_color="rgba(255,255,255,0.3)",
        line_width=2,
        annotation_text="Brake Onset",
        annotation_position="top",
        annotation_font_color="rgba(255,255,255,0.7)",
    )

    # Calculate metrics
    podium_peak_idx = np.argmax(data["podium_pct"])
    rest_peak_idx = np.argmax(data["rest_pct"])
    podium_peak_time = data["time"][podium_peak_idx]
    rest_peak_time = data["time"][rest_peak_idx]

    peak_diff = data["podium_peak"] - data["rest_peak"]
    peak_diff_pct = (peak_diff / data["rest_peak"]) * 100
    time_diff = podium_peak_time - rest_peak_time
    time_diff_pct = (time_diff / rest_peak_time) * 100

    # Dark theme layout
    fig.update_layout(
        title=dict(
            text="Average Brake Curve: Winner vs Field",
            x=0.5,
            xanchor="center",
            y=0.97,
            yanchor="top",
            font=dict(size=24, color="white"),
        ),
        xaxis=dict(
            title=dict(
                text="Time from Brake Onset (seconds)", font=dict(color="white")
            ),
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255,255,255,0.1)",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="rgba(255,255,255,0.2)",
            tickfont=dict(color="white"),
        ),
        yaxis=dict(
            title=dict(text="% of Peak Pressure", font=dict(color="white")),
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255,255,255,0.1)",
            range=[0, 105],
            tickfont=dict(color="white"),
        ),
        height=700,
        width=1400,
        hovermode="x unified",
        plot_bgcolor="rgba(20,20,20,1)",
        paper_bgcolor="rgba(20,20,20,1)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.20,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(26,26,26,0.95)",
            bordercolor="rgba(255,165,0,0.4)",
            borderwidth=1,
            font=dict(size=14, color="white"),
        ),
        margin=dict(l=80, r=20, t=80, b=120),
    )

    return fig


def main():
    """Main execution."""
    print("\n" + "=" * 80)
    print("BRAKE CURVE ANALYSIS: WINNER VS FIELD")
    print("=" * 80)

    # Load data
    brake_events, telemetry, podium_cars = load_data()

    # Calculate threshold
    threshold = calculate_brake_threshold(telemetry)

    # Extract all brake curves
    curves = extract_all_curves(brake_events, telemetry, threshold)

    # Average per driver per zone
    driver_zone_curves = average_curves_per_driver_per_zone(curves)

    # Split double-peak zones
    driver_zone_curves = split_double_zones(driver_zone_curves)

    # Phase-normalize and average
    data = phase_normalize_and_average(driver_zone_curves, podium_cars)

    # Create visualization
    fig = create_visualization(data)

    # Save
    output_path = ANALYTICS_OUTPUT / "brake_curve_winner_vs_field.html"
    fig.write_html(str(output_path), config={"displayModeBar": False})
    print(f"\n✓ Saved: {output_path}")

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
