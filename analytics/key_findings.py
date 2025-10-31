# ABOUTME: Analysis script for extracting key findings from brake point data
# ABOUTME: Compares winner vs podium vs mid-pack consistency and brake point patterns

import pandas as pd
import numpy as np
from pathlib import Path

# Paths to data files
DATA_DIR = Path(__file__).parent.parent / "deliverables" / "data" / "output"
DRIVER_SUMMARY = DATA_DIR / "driver_summary.csv"
BRAKE_EVENTS = DATA_DIR / "brake_events.csv"
ZONE_CENTROIDS = DATA_DIR / "zone_centroids.csv"


def load_data():
    """Load all analysis data files."""
    print("Loading data...")
    drivers = pd.read_csv(DRIVER_SUMMARY)
    events = pd.read_csv(BRAKE_EVENTS)
    centroids = pd.read_csv(ZONE_CENTROIDS)

    # Remove drivers without lap times (incomplete data)
    drivers = drivers[drivers["fastest_lap_seconds"].notna()].copy()

    print(f"✓ Loaded {len(drivers)} drivers with complete data")
    print(f"✓ Loaded {len(events):,} brake events")
    print(f"✓ Loaded {len(centroids)} zone centroids")

    return drivers, events, centroids


def analyze_consistency_by_performance(drivers):
    """
    Compare brake point consistency (dispersion) across performance tiers.

    Returns: Dict with statistics for winner, podium, and mid-pack
    """
    print("\n" + "=" * 80)
    print("ANALYSIS 1: CONSISTENCY BY PERFORMANCE TIER")
    print("=" * 80)

    # Sort by fastest lap
    drivers_sorted = drivers.sort_values("fastest_lap_seconds").reset_index(drop=True)

    # Define tiers
    winner = drivers_sorted.iloc[0]
    podium = drivers_sorted.iloc[:3]  # Top 3
    top_half = drivers_sorted.iloc[: len(drivers_sorted) // 2]
    bottom_half = drivers_sorted.iloc[len(drivers_sorted) // 2 :]

    print(
        f"\nWinner: Car #{int(winner['vehicle_number'])} - {winner['fastest_lap_time']}"
    )
    print(f"  Avg dispersion: {winner['avg_dispersion_meters']:.2f}m")
    print(f"  Total brake events: {int(winner['total_brake_count'])}")

    print("\nPodium finishers (Top 3):")
    for idx, row in podium.iterrows():
        print(
            f"  #{int(row['vehicle_number'])}: {row['fastest_lap_time']} | "
            f"dispersion: {row['avg_dispersion_meters']:.2f}m"
        )

    print(f"\nTop half avg: {top_half['avg_dispersion_meters'].mean():.2f}m")
    print(f"Bottom half avg: {bottom_half['avg_dispersion_meters'].mean():.2f}m")

    # Calculate percentage differences
    podium_avg = podium["avg_dispersion_meters"].mean()
    field_avg = drivers_sorted["avg_dispersion_meters"].mean()
    improvement_pct = ((field_avg - podium_avg) / field_avg) * 100

    print("\n📊 KEY FINDING:")
    print(f"   Podium finishers: {podium_avg:.2f}m average dispersion")
    print(f"   Full field: {field_avg:.2f}m average dispersion")
    print(f"   Podium finishers are {improvement_pct:.1f}% more consistent")

    return {
        "winner_dispersion": winner["avg_dispersion_meters"],
        "winner_car": int(winner["vehicle_number"]),
        "winner_time": winner["fastest_lap_time"],
        "podium_avg_dispersion": podium_avg,
        "field_avg_dispersion": field_avg,
        "improvement_pct": improvement_pct,
        "top_half_avg": top_half["avg_dispersion_meters"].mean(),
        "bottom_half_avg": bottom_half["avg_dispersion_meters"].mean(),
    }


def analyze_zone_patterns(drivers, events, centroids):
    """
    Analyze brake point differences by corner zone for podium vs field.

    Returns: Dict with per-zone statistics
    """
    print("\n" + "=" * 80)
    print("ANALYSIS 2: BRAKE POINT PATTERNS BY ZONE")
    print("=" * 80)

    # Get podium drivers
    drivers_sorted = drivers.sort_values("fastest_lap_seconds").reset_index(drop=True)
    podium_cars = set(drivers_sorted.iloc[:3]["vehicle_number"].astype(int))

    print(f"\nPodium cars: {sorted(podium_cars)}")

    # Filter events to only those with zone assignments
    events_zoned = events[events["zone_id"].notna()].copy()
    events_zoned["is_podium"] = events_zoned["vehicle_number"].isin(podium_cars)

    # Calculate per-zone dispersion for podium vs field
    zone_stats = []

    for zone_id in sorted(events_zoned["zone_id"].unique()):
        zone_events = events_zoned[events_zoned["zone_id"] == zone_id]

        podium_events = zone_events[zone_events["is_podium"]]
        field_events = zone_events[~zone_events["is_podium"]]

        if len(podium_events) > 0 and len(field_events) > 0:
            # Calculate dispersion (standard deviation of GPS positions)
            podium_dispersion = np.sqrt(
                podium_events["x_meters"].std() ** 2
                + podium_events["y_meters"].std() ** 2
            )
            field_dispersion = np.sqrt(
                field_events["x_meters"].std() ** 2
                + field_events["y_meters"].std() ** 2
            )

            # Calculate average brake point position difference
            podium_x_avg = podium_events["x_meters"].mean()
            podium_y_avg = podium_events["y_meters"].mean()
            field_x_avg = field_events["x_meters"].mean()
            field_y_avg = field_events["y_meters"].mean()

            position_diff = np.sqrt(
                (podium_x_avg - field_x_avg) ** 2 + (podium_y_avg - field_y_avg) ** 2
            )

            zone_stats.append(
                {
                    "zone_id": int(zone_id),
                    "podium_dispersion": podium_dispersion,
                    "field_dispersion": field_dispersion,
                    "position_diff_meters": position_diff,
                    "podium_count": len(podium_events),
                    "field_count": len(field_events),
                }
            )

    zone_df = pd.DataFrame(zone_stats)

    print("\nZone-by-zone comparison:")
    print(zone_df.to_string(index=False))

    # Find zones with biggest differences
    zone_df["consistency_advantage"] = (
        zone_df["field_dispersion"] - zone_df["podium_dispersion"]
    )
    zone_df = zone_df.sort_values("consistency_advantage", ascending=False)

    print("\n📊 KEY FINDING - Zones with biggest consistency advantage:")
    for idx, row in zone_df.head(3).iterrows():
        print(
            f"   Zone {row['zone_id']}: Podium {row['podium_dispersion']:.1f}m vs "
            f"Field {row['field_dispersion']:.1f}m "
            f"({row['consistency_advantage']:.1f}m advantage)"
        )

    # Find zones where podium brakes differently
    zone_df_sorted_by_diff = zone_df.sort_values(
        "position_diff_meters", ascending=False
    )
    print("\n📊 KEY FINDING - Zones where podium brakes differently:")
    for idx, row in zone_df_sorted_by_diff.head(3).iterrows():
        print(
            f"   Zone {row['zone_id']}: {row['position_diff_meters']:.1f}m difference in brake point position"
        )

    return zone_df


def analyze_brake_type_patterns(drivers, events):
    """
    Analyze front vs rear brake usage patterns.

    Returns: Dict with brake type statistics
    """
    print("\n" + "=" * 80)
    print("ANALYSIS 3: BRAKE TYPE PATTERNS")
    print("=" * 80)

    # Get podium drivers
    drivers_sorted = drivers.sort_values("fastest_lap_seconds").reset_index(drop=True)
    podium_cars = set(drivers_sorted.iloc[:3]["vehicle_number"].astype(int))

    events_typed = events[events["brake_type"].notna()].copy()
    events_typed["is_podium"] = events_typed["vehicle_number"].isin(podium_cars)

    # Count brake type usage
    podium_brake_types = events_typed[events_typed["is_podium"]][
        "brake_type"
    ].value_counts()
    field_brake_types = events_typed[~events_typed["is_podium"]][
        "brake_type"
    ].value_counts()

    print("\nPodium brake type distribution:")
    print(
        f"  Front-led: {podium_brake_types.get('front', 0)} ({100 * podium_brake_types.get('front', 0) / podium_brake_types.sum():.1f}%)"
    )
    print(
        f"  Rear-led: {podium_brake_types.get('rear', 0)} ({100 * podium_brake_types.get('rear', 0) / podium_brake_types.sum():.1f}%)"
    )

    print("\nField brake type distribution:")
    print(
        f"  Front-led: {field_brake_types.get('front', 0)} ({100 * field_brake_types.get('front', 0) / field_brake_types.sum():.1f}%)"
    )
    print(
        f"  Rear-led: {field_brake_types.get('rear', 0)} ({100 * field_brake_types.get('rear', 0) / field_brake_types.sum():.1f}%)"
    )

    # Calculate average brake pressure
    podium_avg_pressure = events_typed[events_typed["is_podium"]][
        "brake_pressure"
    ].mean()
    field_avg_pressure = events_typed[~events_typed["is_podium"]][
        "brake_pressure"
    ].mean()

    print("\n📊 KEY FINDING:")
    print(f"   Podium avg brake pressure: {podium_avg_pressure:.2f} bar")
    print(f"   Field avg brake pressure: {field_avg_pressure:.2f} bar")

    return {
        "podium_front_pct": 100
        * podium_brake_types.get("front", 0)
        / podium_brake_types.sum(),
        "field_front_pct": 100
        * field_brake_types.get("front", 0)
        / field_brake_types.sum(),
        "podium_avg_pressure": podium_avg_pressure,
        "field_avg_pressure": field_avg_pressure,
    }


def generate_summary_report(consistency_stats, zone_df, brake_type_stats):
    """Generate a summary report for README inclusion."""
    print("\n" + "=" * 80)
    print("SUMMARY REPORT FOR README")
    print("=" * 80)

    print("\n## Key Findings\n")
    print(
        f"Analysis of {consistency_stats['winner_car']} drivers from Barber Motorsports Park:"
    )
    print()
    print(
        f"- **Podium finishers are {consistency_stats['improvement_pct']:.1f}% more consistent** "
        f"in brake point placement ({consistency_stats['podium_avg_dispersion']:.1f}m avg dispersion "
        f"vs {consistency_stats['field_avg_dispersion']:.1f}m for full field)"
    )
    print()

    # Top consistency advantage zones
    top_zones = zone_df.nlargest(2, "consistency_advantage")
    if len(top_zones) > 0:
        zone_1 = top_zones.iloc[0]
        print(
            f"- **Zone {int(zone_1['zone_id'])} shows the clearest performance gap**: "
            f"Podium finishers maintain {zone_1['podium_dispersion']:.1f}m dispersion "
            f"vs {zone_1['field_dispersion']:.1f}m for mid-pack "
            f"({zone_1['consistency_advantage']:.1f}m advantage)"
        )
        print()

    # Brake point position differences
    top_diff_zones = zone_df.nlargest(2, "position_diff_meters")
    if len(top_diff_zones) > 0:
        zone_2 = top_diff_zones.iloc[0]
        print(
            f"- **Podium finishers brake {zone_2['position_diff_meters']:.1f}m differently in Zone {int(zone_2['zone_id'])}**, "
            f"suggesting strategic brake point placement beyond pure consistency"
        )
        print()

    # Winner detail
    print(
        f"- **Winner (Car #{consistency_stats['winner_car']})** achieved {consistency_stats['winner_dispersion']:.1f}m "
        f"average dispersion with fastest lap of {consistency_stats['winner_time']}"
    )
    print()

    # Brake intensity
    if (
        abs(
            brake_type_stats["podium_avg_pressure"]
            - brake_type_stats["field_avg_pressure"]
        )
        > 0.5
    ):
        diff = (
            brake_type_stats["podium_avg_pressure"]
            - brake_type_stats["field_avg_pressure"]
        )
        direction = "higher" if diff > 0 else "lower"
        print(
            f"- **Brake intensity differs**: Podium finishers average {abs(diff):.1f} bar {direction} "
            f"brake pressure ({brake_type_stats['podium_avg_pressure']:.1f} vs "
            f"{brake_type_stats['field_avg_pressure']:.1f} bar)"
        )


def main():
    """Run all analyses and generate report."""
    print("BRAKE POINT ANALYSIS - KEY FINDINGS")
    print("=" * 80)

    # Load data
    drivers, events, centroids = load_data()

    # Run analyses
    consistency_stats = analyze_consistency_by_performance(drivers)
    zone_df = analyze_zone_patterns(drivers, events, centroids)
    brake_type_stats = analyze_brake_type_patterns(drivers, events)

    # Generate summary
    generate_summary_report(consistency_stats, zone_df, brake_type_stats)

    # Save zone analysis to CSV
    output_path = Path(__file__).parent / "zone_comparison.csv"
    zone_df.to_csv(output_path, index=False)
    print(f"\n✓ Saved detailed zone analysis to: {output_path}")


if __name__ == "__main__":
    main()
