# ABOUTME: Load and transform telemetry and USAC results data
# ABOUTME: Handles chunked loading, GPS conversion to meters, and data filtering

import pandas as pd
import numpy as np
from pyproj import Transformer


def load_telemetry(telemetry_path, chunk_size=500000):
    """
    Load telemetry data in chunks, filter to needed parameters, and convert GPS to meters.

    Args:
        telemetry_path: Path to telemetry CSV file
        chunk_size: Number of rows to process at a time

    Returns:
        DataFrame with columns: vehicle_number, lap, timestamp, pbrake_f, pbrake_r,
                                VBOX_Long_Minutes, VBOX_Lat_Min, speed, x_meters, y_meters
    """
    # Parameters we need from telemetry
    needed_params = [
        "pbrake_f",
        "pbrake_r",
        "VBOX_Long_Minutes",
        "VBOX_Lat_Min",
        "speed",
    ]

    print(f"Loading telemetry from {telemetry_path}")
    print(f"Processing in chunks of {chunk_size:,} rows...")

    # Store pivoted chunks
    pivoted_chunks = []
    chunk_count = 0

    # Read in chunks
    for chunk in pd.read_csv(telemetry_path, chunksize=chunk_size):
        chunk_count += 1

        # Filter to only needed telemetry parameters
        chunk_filtered = chunk[chunk["telemetry_name"].isin(needed_params)].copy()

        if len(chunk_filtered) == 0:
            continue

        # Pivot: one row per (vehicle_number, lap, timestamp) with columns for each parameter
        chunk_pivoted = chunk_filtered.pivot_table(
            index=["vehicle_number", "lap", "timestamp"],
            columns="telemetry_name",
            values="telemetry_value",
            aggfunc="first",  # Take first value if duplicates
        ).reset_index()

        pivoted_chunks.append(chunk_pivoted)

        if chunk_count % 10 == 0:
            print(
                f"  Processed {chunk_count} chunks ({chunk_count * chunk_size:,} rows)..."
            )

    print(f"Total chunks processed: {chunk_count}")
    print("Concatenating chunks...")

    # Combine all chunks
    df = pd.concat(pivoted_chunks, ignore_index=True)

    # Drop rows with missing GPS data (can't use without coordinates)
    print(f"Rows before GPS filter: {len(df):,}")
    df = df.dropna(subset=["VBOX_Long_Minutes", "VBOX_Lat_Min"])
    print(f"Rows after GPS filter: {len(df):,}")

    # Convert GPS coordinates to meters using UTM projection
    print("Converting GPS coordinates to meters using UTM projection...")
    df = _convert_gps_to_meters(df)

    print(
        f"Final dataset: {len(df):,} rows, {len(df['vehicle_number'].unique())} vehicles"
    )

    return df


def _convert_gps_to_meters(df):
    """
    Convert GPS lon/lat to local Cartesian coordinates in meters using UTM projection.

    Args:
        df: DataFrame with VBOX_Long_Minutes and VBOX_Lat_Min columns

    Returns:
        DataFrame with added x_meters and y_meters columns
    """
    # Use UTM zone 16N for Alabama (Barber Motorsports Park)
    # EPSG:32616 is UTM zone 16N
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32616", always_xy=True)

    # Convert lon, lat to x, y in meters
    x_meters, y_meters = transformer.transform(
        df["VBOX_Long_Minutes"].values, df["VBOX_Lat_Min"].values
    )

    df["x_meters"] = x_meters
    df["y_meters"] = y_meters

    return df


def load_usac_results(results_path):
    """
    Load USAC timing results.

    Args:
        results_path: Path to USAC results CSV file

    Returns:
        DataFrame with race results including driver numbers and fastest lap times
    """
    print(f"Loading USAC results from {results_path}")

    # USAC files use semicolon delimiter
    df = pd.read_csv(results_path, sep=";")

    # Convert FL_TIME (fastest lap time) to seconds for easier comparison
    df["FL_TIME_seconds"] = pd.to_timedelta(
        "00:" + df["FL_TIME"].astype(str)
    ).dt.total_seconds()

    print(f"Loaded {len(df)} drivers")
    print(
        f"Fastest lap: {df.loc[df['FL_TIME_seconds'].idxmin(), 'FL_TIME']} by car #{df.loc[df['FL_TIME_seconds'].idxmin(), 'NUMBER']}"
    )

    return df


def calculate_brake_threshold(df, percentile=95):
    """
    Calculate brake pressure threshold (P95 by default).

    Args:
        df: Telemetry DataFrame with pbrake_f and pbrake_r columns
        percentile: Percentile threshold (default 95)

    Returns:
        Threshold value in bar
    """
    # Combine front and rear brake pressures
    all_brake_pressures = pd.concat([df["pbrake_f"].dropna(), df["pbrake_r"].dropna()])

    threshold = np.percentile(all_brake_pressures, percentile)

    print(f"P{percentile} brake pressure threshold: {threshold:.2f} bar")
    print(f"Total brake pressure samples: {len(all_brake_pressures):,}")

    return threshold
