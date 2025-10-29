# ABOUTME: Script to generate track outline visualization
# ABOUTME: Loads processed telemetry and creates track visualization

import pandas as pd
from pathlib import Path
from track_rendering import generate_track_outline, save_track_data

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"
OUTPUT_HTML = BASE_DIR / "data" / "visualizations" / "step3_track_outline.html"
OUTPUT_CSV = BASE_DIR / "data" / "gps-tracks" / "track_centerline.csv"


def main():
    print("=" * 80)
    print("STEP 3: Generate Track Outline")
    print("=" * 80)
    print()

    # Load telemetry
    print("Loading telemetry data...")
    df = pd.read_csv(TELEMETRY_PATH)
    print(f"✓ Loaded {len(df):,} rows")
    print()

    # Generate track outline (using car #13 - fastest driver)
    print("Generating track outline...")
    print("-" * 80)
    x_smooth, y_smooth, fig = generate_track_outline(
        df,
        vehicle_number=13,  # Fastest driver from Step 2
        lap_number=None,  # Auto-select best lap
        resample_step_m=2.0,  # Resample every 2m
        spike_threshold_m=10.0,  # Remove GPS spikes >10m
        savgol_window=31,  # Savitzky-Golay window
        savgol_poly=3,  # Polynomial order
        wrap_count=25,  # Points to wrap for periodic smoothing
    )
    print()

    # Save track centerline
    print("Saving track data...")
    print("-" * 80)
    save_track_data(x_smooth, y_smooth, OUTPUT_CSV)
    print()

    # Save HTML visualization
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(OUTPUT_HTML)
    print(f"✓ Saved visualization to: {OUTPUT_HTML}")
    print()

    print("=" * 80)
    print("✓ TRACK OUTLINE COMPLETE")
    print(f"✓ Open {OUTPUT_HTML} in browser to review")
    print("=" * 80)


if __name__ == "__main__":
    main()
