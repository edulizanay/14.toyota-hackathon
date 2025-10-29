# ABOUTME: Script to load and process raw telemetry data
# ABOUTME: Runs the data loading pipeline and saves processed data

import sys
from pathlib import Path
from data_loaders import load_telemetry, load_usac_results, calculate_brake_threshold

# Paths
BASE_DIR = Path(__file__).parent.parent
TELEMETRY_PATH = BASE_DIR / "barber" / "R1_barber_telemetry_data.csv"
USAC_RESULTS_PATH = BASE_DIR / "barber" / "03_Provisional Results_Race 1_Anonymized.CSV"
OUTPUT_PATH = BASE_DIR / "data" / "telemetry-raw" / "all_drivers.csv"

def main():
    print("=" * 80)
    print("BRAKE POINT DRIFT DETECTOR - Data Loading & Transformation")
    print("=" * 80)
    print()

    # Load telemetry data
    print("STEP 1: Loading telemetry data...")
    print("-" * 80)
    df_telemetry = load_telemetry(TELEMETRY_PATH, chunk_size=500000)
    print()

    # Calculate brake threshold (corrected to use P5 of positive pressures)
    print("STEP 2: Calculating brake pressure threshold...")
    print("-" * 80)
    print("Using P5 of positive pressures to detect brake onset (discard lowest 5% as noise)")
    threshold = calculate_brake_threshold(df_telemetry, percentile=5)
    print()

    # Load USAC results
    print("STEP 3: Loading USAC race results...")
    print("-" * 80)
    df_results = load_usac_results(USAC_RESULTS_PATH)
    print()

    # Verify required columns
    print("STEP 4: Verifying data structure...")
    print("-" * 80)
    required_cols = ['vehicle_number', 'lap', 'timestamp', 'pbrake_f', 'pbrake_r',
                     'VBOX_Long_Minutes', 'VBOX_Lat_Min', 'speed', 'x_meters', 'y_meters']

    missing_cols = [col for col in required_cols if col not in df_telemetry.columns]

    if missing_cols:
        print(f"❌ ERROR: Missing required columns: {missing_cols}")
        sys.exit(1)
    else:
        print(f"✓ All required columns present: {required_cols}")

    print(f"✓ Telemetry data shape: {df_telemetry.shape}")
    print(f"✓ Columns: {list(df_telemetry.columns)}")
    print()

    # Show sample
    print("Sample data (first 5 rows):")
    print(df_telemetry.head())
    print()

    # Save processed data
    print("STEP 5: Saving processed data...")
    print("-" * 80)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_telemetry.to_csv(OUTPUT_PATH, index=False)
    print(f"✓ Saved to: {OUTPUT_PATH}")
    print(f"✓ File size: {OUTPUT_PATH.stat().st_size / (1024**2):.1f} MB")
    print()

    print("=" * 80)
    print("✓ DATA LOADING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
