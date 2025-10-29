# ABOUTME: Detect brake onset events from telemetry data
# ABOUTME: Uses rising-edge detection to identify first brake application per event

import pandas as pd
import numpy as np


def detect_brake_events(df, threshold):
    """
    Detect brake onset events using rising-edge detection.

    Args:
        df: Telemetry DataFrame with pbrake_f, pbrake_r, x_meters, y_meters, timestamp, lap, vehicle_number
        threshold: Brake pressure threshold in bar (from P5 calculation)

    Returns:
        DataFrame with brake onset events: vehicle_number, lap, timestamp, x_meters, y_meters,
                                          brake_pressure, brake_type (front/rear)
    """
    print(f"Detecting brake events with threshold: {threshold:.2f} bar")

    # Sort by vehicle, lap, and timestamp to ensure correct order
    df = df.sort_values(["vehicle_number", "lap", "timestamp"]).copy()

    # Combine front and rear brake pressures (use max)
    df["brake_pressure"] = df[["pbrake_f", "pbrake_r"]].max(axis=1)

    # Determine which brake led (front or rear)
    df["brake_type"] = np.where(df["pbrake_f"] >= df["pbrake_r"], "front", "rear")

    # Mark samples where braking (pressure >= threshold)
    df["is_braking"] = df["brake_pressure"] >= threshold

    # Detect rising edges (transition from not braking to braking)
    # Group by vehicle and lap to handle edge detection per stint
    brake_events = []

    for (vehicle, lap), group in df.groupby(["vehicle_number", "lap"]):
        # Shift is_braking to detect transitions
        prev_braking = group["is_braking"].shift(1, fill_value=False)
        rising_edge = group["is_braking"] & (~prev_braking)

        # Extract brake onset events
        onsets = group[rising_edge].copy()

        if len(onsets) > 0:
            brake_events.append(
                onsets[
                    [
                        "vehicle_number",
                        "lap",
                        "timestamp",
                        "x_meters",
                        "y_meters",
                        "VBOX_Long_Minutes",
                        "VBOX_Lat_Min",
                        "brake_pressure",
                        "brake_type",
                        "pbrake_f",
                        "pbrake_r",
                    ]
                ]
            )

    if len(brake_events) == 0:
        print("❌ WARNING: No brake events detected!")
        return pd.DataFrame()

    # Combine all events
    df_events = pd.concat(brake_events, ignore_index=True)

    print(f"✓ Detected {len(df_events):,} brake onset events")
    print(
        f"  Events per vehicle (avg): {len(df_events) / df['vehicle_number'].nunique():.1f}"
    )
    print(
        f"  Front brake led: {(df_events['brake_type'] == 'front').sum():,} ({100 * (df_events['brake_type'] == 'front').sum() / len(df_events):.1f}%)"
    )
    print(
        f"  Rear brake led: {(df_events['brake_type'] == 'rear').sum():,} ({100 * (df_events['brake_type'] == 'rear').sum() / len(df_events):.1f}%)"
    )

    return df_events


def filter_brake_events_by_pressure(df_events, min_pressure=None, max_pressure=None):
    """
    Filter brake events by pressure range (optional post-processing).

    Args:
        df_events: DataFrame of brake events
        min_pressure: Minimum brake pressure to include
        max_pressure: Maximum brake pressure to include

    Returns:
        Filtered DataFrame
    """
    df_filtered = df_events.copy()

    if min_pressure is not None:
        df_filtered = df_filtered[df_filtered["brake_pressure"] >= min_pressure]
        print(f"Filtered to >= {min_pressure} bar: {len(df_filtered):,} events")

    if max_pressure is not None:
        df_filtered = df_filtered[df_filtered["brake_pressure"] <= max_pressure]
        print(f"Filtered to <= {max_pressure} bar: {len(df_filtered):,} events")

    return df_filtered
