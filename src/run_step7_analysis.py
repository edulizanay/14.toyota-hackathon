# ABOUTME: Step 7: Calculate dispersion and validate hypothesis
# ABOUTME: Critical validation step - tests if faster drivers have lower dispersion

import matplotlib.pyplot as plt
from pathlib import Path
from consistency_analysis import (
    load_brake_events,
    calculate_dispersion_by_zone,
    calculate_driver_summary,
    add_lap_times,
    validate_hypothesis,
)

# Paths
BASE_DIR = Path(__file__).parent.parent
USAC_RESULTS = BASE_DIR / "barber" / "03_Provisional Results_Race 1_Anonymized.CSV"
OUTPUT_DIR_SCORES = BASE_DIR / "data" / "consistency-scores"
OUTPUT_DIR_VIZ = BASE_DIR / "data" / "visualizations"
DISPERSION_BY_CORNER = OUTPUT_DIR_SCORES / "dispersion_by_corner.csv"
DRIVER_SUMMARY = OUTPUT_DIR_SCORES / "driver_summary.csv"
SCATTER_PLOT = OUTPUT_DIR_VIZ / "step7_correlation.png"


def main():
    print("=" * 80)
    print("STEP 7: Calculate Dispersion & Validate Hypothesis")
    print("=" * 80)
    print()

    # Load brake events
    print("Loading brake events...")
    brake_events = load_brake_events()
    print(f"✓ Loaded {len(brake_events):,} brake events")
    print()

    # Calculate dispersion by zone
    print("Calculating dispersion per driver per zone...")
    dispersion_by_zone = calculate_dispersion_by_zone(brake_events)
    print(
        f"✓ Calculated dispersion for {len(dispersion_by_zone)} driver-zone combinations"
    )
    print()

    # Show sample
    print("Sample dispersion data:")
    print(dispersion_by_zone.head(10).to_string(index=False))
    print()

    # Calculate driver summary
    print("Calculating driver summary (average across zones)...")
    driver_summary = calculate_driver_summary(dispersion_by_zone)
    print(f"✓ Calculated summary for {len(driver_summary)} drivers")
    print()

    # Add lap times from USAC results
    print("Loading USAC results and adding lap times...")
    if not USAC_RESULTS.exists():
        print(f"ERROR: USAC results file not found at {USAC_RESULTS}")
        return

    driver_summary_with_times = add_lap_times(driver_summary, USAC_RESULTS)
    print(
        f"✓ Added lap times for {driver_summary_with_times['fastest_lap_seconds'].notna().sum()} drivers"
    )
    print()

    # Sort by lap time and display
    print("Driver rankings (sorted by lap time):")
    print("-" * 80)
    ranked = driver_summary_with_times.dropna(
        subset=["fastest_lap_seconds"]
    ).sort_values("fastest_lap_seconds")
    display_cols = [
        "vehicle_number",
        "fastest_lap_time",
        "avg_dispersion_meters",
        "zone_count",
        "total_brake_count",
    ]
    print(ranked[display_cols].to_string(index=False))
    print()

    # CRITICAL VALIDATION
    print("=" * 80)
    print("CRITICAL VALIDATION: Testing Hypothesis")
    print("=" * 80)
    hypothesis_holds, message = validate_hypothesis(driver_summary_with_times)
    print(message)

    if not hypothesis_holds:
        print()
        print("🛑 WARNING: HYPOTHESIS FAILED")
        print(
            "🛑 The assumption that faster drivers have lower dispersion does NOT hold!"
        )
        print("🛑 We need to stop and reassess the approach.")
        print()
        print("Saving data for review...")
    else:
        print()
        print("✓ Hypothesis validated! Proceeding with visualization...")
        print()

    # Save CSV files
    print("Saving consistency scores...")
    OUTPUT_DIR_SCORES.mkdir(parents=True, exist_ok=True)

    dispersion_by_zone.to_csv(DISPERSION_BY_CORNER, index=False)
    print(f"✓ Saved: {DISPERSION_BY_CORNER}")

    driver_summary_with_times.to_csv(DRIVER_SUMMARY, index=False)
    print(f"✓ Saved: {DRIVER_SUMMARY}")
    print()

    # Create scatter plot
    print("Creating scatter plot...")
    valid_data = driver_summary_with_times.dropna(subset=["fastest_lap_seconds"])

    fig, ax = plt.subplots(figsize=(10, 6))

    # Scatter plot
    ax.scatter(
        valid_data["fastest_lap_seconds"],
        valid_data["avg_dispersion_meters"],
        s=100,
        alpha=0.6,
        color="#4ECDC4",
        edgecolors="black",
        linewidth=1.5,
    )

    # Add labels for each point
    for _, row in valid_data.iterrows():
        ax.annotate(
            f"#{int(row['vehicle_number'])}",
            (row["fastest_lap_seconds"], row["avg_dispersion_meters"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            alpha=0.7,
        )

    # Styling
    ax.set_xlabel("Fastest Lap Time (seconds)", fontsize=12, fontweight="bold")
    ax.set_ylabel(
        "Average Brake Point Dispersion (meters)", fontsize=12, fontweight="bold"
    )
    ax.set_title(
        "Lap Time vs Brake Point Consistency\nBarber Motorsports Park - Race 1",
        fontsize=14,
        fontweight="bold",
    )
    ax.grid(True, alpha=0.3, linestyle="--")

    # Add correlation annotation
    correlation = valid_data["fastest_lap_seconds"].corr(
        valid_data["avg_dispersion_meters"]
    )
    ax.text(
        0.05,
        0.95,
        f"Correlation: {correlation:.3f}",
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    OUTPUT_DIR_VIZ.mkdir(parents=True, exist_ok=True)
    plt.savefig(SCATTER_PLOT, dpi=150, bbox_inches="tight")
    print(f"✓ Saved scatter plot: {SCATTER_PLOT}")
    print()

    print("=" * 80)
    if hypothesis_holds:
        print("✓ STEP 7 COMPLETE - Hypothesis validated, ready for Step 8")
    else:
        print("🛑 STEP 7 HALTED - Please review results with Edu before proceeding")
    print("=" * 80)


if __name__ == "__main__":
    main()
