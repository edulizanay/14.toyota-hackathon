# ABOUTME: Consistency analysis utilities for brake point dispersion
# ABOUTME: Calculates std dev of brake points per driver per zone

import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
BRAKE_EVENTS_CSV = BASE_DIR / "data" / "brake-analysis" / "brake_events.csv"


def load_brake_events():
    """Load brake events CSV."""
    return pd.read_csv(BRAKE_EVENTS_CSV)


def calculate_dispersion_by_zone(brake_events_df):
    """
    Calculate brake point dispersion (std dev) per driver per zone.

    Returns:
        DataFrame with columns: vehicle_number, zone_id, dispersion_meters, brake_count
    """
    # Filter to only brake events within zones
    in_zone = brake_events_df[brake_events_df["zone_id"].notna()].copy()

    results = []

    for (vehicle, zone), group in in_zone.groupby(["vehicle_number", "zone_id"]):
        if len(group) < 2:
            # Need at least 2 points to calculate std dev
            continue

        # Calculate std dev in x and y
        std_x = group["x_meters"].std()
        std_y = group["y_meters"].std()

        # Euclidean std dev (dispersion in meters)
        dispersion = np.sqrt(std_x**2 + std_y**2)

        results.append({
            "vehicle_number": vehicle,
            "zone_id": zone,
            "dispersion_meters": dispersion,
            "brake_count": len(group),
            "std_x": std_x,
            "std_y": std_y,
        })

    return pd.DataFrame(results)


def calculate_driver_summary(dispersion_by_zone_df):
    """
    Calculate average dispersion across all zones per driver.

    Returns:
        DataFrame with columns: vehicle_number, avg_dispersion_meters, zone_count, total_brake_count
    """
    summary = dispersion_by_zone_df.groupby("vehicle_number").agg({
        "dispersion_meters": "mean",
        "zone_id": "count",
        "brake_count": "sum",
    }).reset_index()

    summary.columns = ["vehicle_number", "avg_dispersion_meters", "zone_count", "total_brake_count"]

    return summary


def add_lap_times(driver_summary_df, usac_results_path):
    """
    Add lap time data from USAC results.

    Args:
        driver_summary_df: DataFrame with vehicle_number column
        usac_results_path: Path to USAC results CSV

    Returns:
        DataFrame with added fastest_lap_time column
    """
    # Load USAC results (semicolon-separated)
    usac = pd.read_csv(usac_results_path, sep=";")

    # Extract relevant columns: NUMBER (car number), FL_TIME (fastest lap time)
    # FL_TIME is in format "M:SS.mmm" (e.g., "1:37.428")
    usac_clean = usac[["NUMBER", "FL_TIME"]].copy()
    usac_clean.columns = ["vehicle_number", "fastest_lap_time"]

    # Convert lap time to seconds
    def lap_time_to_seconds(time_str):
        if pd.isna(time_str) or time_str == "":
            return np.nan
        try:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        except:
            return np.nan

    usac_clean["fastest_lap_seconds"] = usac_clean["fastest_lap_time"].apply(lap_time_to_seconds)

    # Merge with driver summary
    merged = driver_summary_df.merge(
        usac_clean[["vehicle_number", "fastest_lap_time", "fastest_lap_seconds"]],
        on="vehicle_number",
        how="left"
    )

    return merged


def validate_hypothesis(driver_summary_with_times_df):
    """
    Validate core hypothesis: faster drivers should have lower dispersion.

    Returns:
        bool: True if hypothesis holds, False otherwise
        str: Validation message
    """
    # Remove drivers without lap times
    valid = driver_summary_with_times_df.dropna(subset=["fastest_lap_seconds"]).copy()

    if len(valid) == 0:
        return False, "No valid lap time data found"

    # Sort by lap time
    valid_sorted = valid.sort_values("fastest_lap_seconds")

    # Check correlation
    correlation = valid["fastest_lap_seconds"].corr(valid["avg_dispersion_meters"])

    # Get fastest and slowest drivers
    fastest_driver = valid_sorted.iloc[0]
    slowest_driver = valid_sorted.iloc[-1]

    # Simple validation: fastest should have lower dispersion than slowest
    fastest_better = fastest_driver["avg_dispersion_meters"] < slowest_driver["avg_dispersion_meters"]

    # Check if correlation is positive (faster time = higher dispersion)
    positive_correlation = correlation > 0

    message = f"""
Hypothesis Validation Results:
==============================

Fastest driver: #{fastest_driver['vehicle_number']:.0f}
  Lap time: {fastest_driver['fastest_lap_time']}
  Avg dispersion: {fastest_driver['avg_dispersion_meters']:.2f}m

Slowest driver: #{slowest_driver['vehicle_number']:.0f}
  Lap time: {slowest_driver['fastest_lap_time']}
  Avg dispersion: {slowest_driver['avg_dispersion_meters']:.2f}m

Correlation (lap_time vs dispersion): {correlation:.3f}

Fastest driver has lower dispersion: {fastest_better}
Positive correlation: {positive_correlation}

Hypothesis: {'✓ VALIDATED' if (fastest_better and positive_correlation) else '✗ FAILED'}
"""

    hypothesis_holds = fastest_better and positive_correlation

    return hypothesis_holds, message
