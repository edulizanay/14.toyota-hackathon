# ABOUTME: Public API exports for visuals package
# ABOUTME: Re-exports main functions used by pipeline (main.py)

from .geometry import (
    resample_by_distance,
    smooth_periodic,
    compute_normals,
    rotate_coordinates,
)

from .track_outline import (
    compute_centerline,
    save_centerline,
    load_centerline,
    make_base_track_figure,
)

from .dashboards import (
    DRIVER_COLORS,
    create_zone_focused_dashboard,
    render_zone_focus_dashboard,
)

__all__ = [
    # Geometry functions
    "resample_by_distance",
    "smooth_periodic",
    "compute_normals",
    "rotate_coordinates",
    # Track outline functions
    "compute_centerline",
    "save_centerline",
    "load_centerline",
    "make_base_track_figure",
    # Dashboard functions
    "DRIVER_COLORS",
    "create_zone_focused_dashboard",
    "render_zone_focus_dashboard",
]
