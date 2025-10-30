# ABOUTME: Corner/zone detection and brake point assignment utilities
# ABOUTME: Implements track-distance-based zone assignment for brake events

import json
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CORNER_DEFINITIONS_JSON = (
    BASE_DIR / "data" / "brake-analysis" / "corner_definitions.json"
)


def load_zone_definitions():
    """Load brake zone definitions from JSON file."""
    with open(CORNER_DEFINITIONS_JSON, "r") as f:
        return json.load(f)


def project_to_centerline(points_x, points_y, centerline_x, centerline_y):
    """
    Project points onto track centerline and return track distances.

    Args:
        points_x: Array of x coordinates to project
        points_y: Array of y coordinates to project
        centerline_x: Array of centerline x coordinates
        centerline_y: Array of centerline y coordinates

    Returns:
        Array of track distances (meters from start)
    """
    # Calculate cumulative distance along centerline
    dx = np.diff(centerline_x)
    dy = np.diff(centerline_y)
    segment_lengths = np.sqrt(dx**2 + dy**2)
    cumulative_distance = np.concatenate([[0], np.cumsum(segment_lengths)])

    # For each point, find nearest centerline point
    track_distances = []

    for px, py in zip(points_x, points_y):
        distances = np.sqrt((centerline_x - px) ** 2 + (centerline_y - py) ** 2)
        nearest_idx = np.argmin(distances)
        track_distances.append(cumulative_distance[nearest_idx])

    return np.array(track_distances)


def assign_to_zones(brake_events_df, centerline_x, centerline_y):
    """
    Assign brake events to zones based on track distance.

    Args:
        brake_events_df: DataFrame with x_meters, y_meters columns
        centerline_x: Array of centerline x coordinates
        centerline_y: Array of centerline y coordinates

    Returns:
        DataFrame with added track_distance and zone_id columns
    """
    # Load zone definitions
    zones = load_zone_definitions()

    # Project brake points to track distance
    track_distances = project_to_centerline(
        brake_events_df["x_meters"].values,
        brake_events_df["y_meters"].values,
        centerline_x,
        centerline_y,
    )

    brake_events_df = brake_events_df.copy()
    brake_events_df["track_distance"] = track_distances

    # Assign to zones
    def assign_zone(distance):
        for zone in zones:
            if zone["start_distance_m"] <= distance <= zone["end_distance_m"]:
                return zone["zone_id"]
        return None

    brake_events_df["zone_id"] = brake_events_df["track_distance"].apply(assign_zone)

    return brake_events_df


def calculate_zone_boundaries(brake_events_df, padding_m=20.0, save_path=None):
    """
    Calculate spatial boundaries (bounding box) for each brake zone.

    Args:
        brake_events_df: DataFrame with brake events (must have zone_id, x_meters, y_meters)
        padding_m: Padding in meters to add around each zone (default: 20m)
        save_path: Optional path to save boundaries as JSON

    Returns:
        dict: {zone_id: {x_min, x_max, y_min, y_max, center_x, center_y}}
    """
    bounds = {}
    grouped = brake_events_df[brake_events_df["zone_id"].notna()].groupby("zone_id")

    for zid, dfz in grouped:
        xmin, xmax = dfz["x_meters"].min(), dfz["x_meters"].max()
        ymin, ymax = dfz["y_meters"].min(), dfz["y_meters"].max()

        # Add padding
        xmin -= padding_m
        xmax += padding_m
        ymin -= padding_m
        ymax += padding_m

        bounds[int(zid)] = {
            "x_min": float(xmin),
            "x_max": float(xmax),
            "y_min": float(ymin),
            "y_max": float(ymax),
            "center_x": float((xmin + xmax) / 2.0),
            "center_y": float((ymin + ymax) / 2.0),
        }

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(json.dumps(bounds, indent=2))

    return bounds
