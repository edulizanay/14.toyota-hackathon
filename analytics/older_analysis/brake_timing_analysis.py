# ABOUTME: Analysis of brake timing - does winner brake earlier or later?
# ABOUTME: Compares track distance at brake onset for winner vs podium vs field

import pandas as pd
from pathlib import Path

# Paths to data files
DATA_DIR = Path(__file__).parent.parent / "deliverables" / "data" / "output"
DRIVER_SUMMARY = DATA_DIR / "driver_summary.csv"
BRAKE_EVENTS = DATA_DIR / "brake_events.csv"


def load_data():
    """Load driver summary and brake events."""
    print("Loading data...")
    drivers = pd.read_csv(DRIVER_SUMMARY)
    events = pd.read_csv(BRAKE_EVENTS)

    # Remove drivers without lap times
    drivers = drivers[drivers["fastest_lap_seconds"].notna()].copy()

    print(f"✓ Loaded {len(drivers)} drivers with complete data")
    print(f"✓ Loaded {len(events):,} brake events")

    return drivers, events


def analyze_brake_timing_by_zone(drivers, events):
    """
    Analyze whether winner/podium brake earlier or later than field by zone.
    Uses track_distance to measure brake point position along the track.
    """
    print("\n" + "=" * 80)
    print("BRAKE TIMING ANALYSIS - EARLIER VS LATER BRAKING")
    print("=" * 80)

    # Get winner and podium
    drivers_sorted = drivers.sort_values("fastest_lap_seconds").reset_index(drop=True)
    winner = drivers_sorted.iloc[0]
    winner_car = int(winner["vehicle_number"])
    podium_cars = set(drivers_sorted.iloc[:3]["vehicle_number"].astype(int))

    print(f"\nWinner: Car #{winner_car} - {winner['fastest_lap_time']}")
    print(f"Podium: {sorted(podium_cars)}")

    # Filter to events with zone assignments and track distance
    events_zoned = events[
        events["zone_id"].notna() & events["track_distance"].notna()
    ].copy()
    events_zoned["is_winner"] = events_zoned["vehicle_number"] == winner_car
    events_zoned["is_podium"] = events_zoned["vehicle_number"].isin(podium_cars)

    # Analyze by zone
    zone_timing = []

    for zone_id in sorted(events_zoned["zone_id"].unique()):
        zone_events = events_zoned[events_zoned["zone_id"] == zone_id]

        winner_events = zone_events[zone_events["is_winner"]]
        podium_events = zone_events[zone_events["is_podium"]]
        field_events = zone_events[~zone_events["is_podium"]]

        if len(winner_events) > 0 and len(field_events) > 0:
            # Average track distance at brake onset
            winner_avg_dist = winner_events["track_distance"].mean()
            podium_avg_dist = podium_events["track_distance"].mean()
            field_avg_dist = field_events["track_distance"].mean()

            # Negative difference = braking earlier (smaller track distance)
            winner_diff = winner_avg_dist - field_avg_dist
            podium_diff = podium_avg_dist - field_avg_dist

            zone_timing.append(
                {
                    "zone_id": int(zone_id),
                    "winner_avg_dist": winner_avg_dist,
                    "podium_avg_dist": podium_avg_dist,
                    "field_avg_dist": field_avg_dist,
                    "winner_diff_meters": winner_diff,
                    "podium_diff_meters": podium_diff,
                    "winner_brakes": "earlier"
                    if winner_diff < -1
                    else ("later" if winner_diff > 1 else "same"),
                    "podium_brakes": "earlier"
                    if podium_diff < -1
                    else ("later" if podium_diff > 1 else "same"),
                }
            )

    timing_df = pd.DataFrame(zone_timing)

    print("\nZone-by-zone brake timing comparison:")
    print("(Negative = braking earlier, Positive = braking later)")
    print()
    print(
        timing_df[
            [
                "zone_id",
                "winner_diff_meters",
                "podium_diff_meters",
                "winner_brakes",
                "podium_brakes",
            ]
        ].to_string(index=False)
    )

    # Summary statistics
    winner_earlier_count = (timing_df["winner_diff_meters"] < -1).sum()
    winner_later_count = (timing_df["winner_diff_meters"] > 1).sum()
    winner_same_count = len(timing_df) - winner_earlier_count - winner_later_count

    podium_earlier_count = (timing_df["podium_diff_meters"] < -1).sum()
    podium_later_count = (timing_df["podium_diff_meters"] > 1).sum()
    podium_same_count = len(timing_df) - podium_earlier_count - podium_later_count

    print("\n📊 WINNER BRAKE TIMING SUMMARY:")
    print(f"   Brakes earlier: {winner_earlier_count}/{len(timing_df)} zones")
    print(f"   Brakes later: {winner_later_count}/{len(timing_df)} zones")
    print(f"   Same timing: {winner_same_count}/{len(timing_df)} zones")

    print("\n📊 PODIUM BRAKE TIMING SUMMARY:")
    print(f"   Brakes earlier: {podium_earlier_count}/{len(timing_df)} zones")
    print(f"   Brakes later: {podium_later_count}/{len(timing_df)} zones")
    print(f"   Same timing: {podium_same_count}/{len(timing_df)} zones")

    # Average differences
    avg_winner_diff = timing_df["winner_diff_meters"].mean()
    avg_podium_diff = timing_df["podium_diff_meters"].mean()

    print("\n📊 AVERAGE BRAKE POINT DIFFERENCE:")
    print(
        f"   Winner: {avg_winner_diff:.1f}m {'earlier' if avg_winner_diff < 0 else 'later'} than field average"
    )
    print(
        f"   Podium: {avg_podium_diff:.1f}m {'earlier' if avg_podium_diff < 0 else 'later'} than field average"
    )

    # Most significant differences
    print("\n📊 ZONES WITH BIGGEST TIMING DIFFERENCES (Winner vs Field):")
    timing_df["abs_winner_diff"] = timing_df["winner_diff_meters"].abs()
    top_diffs = timing_df.nlargest(3, "abs_winner_diff")

    for idx, row in top_diffs.iterrows():
        direction = "earlier" if row["winner_diff_meters"] < 0 else "later"
        print(
            f"   Zone {row['zone_id']}: {abs(row['winner_diff_meters']):.1f}m {direction}"
        )

    return timing_df


def analyze_overall_brake_timing(drivers, events):
    """
    Overall analysis of brake timing across all zones.
    """
    print("\n" + "=" * 80)
    print("OVERALL BRAKE TIMING PATTERN")
    print("=" * 80)

    # Get winner and podium
    drivers_sorted = drivers.sort_values("fastest_lap_seconds").reset_index(drop=True)
    winner_car = int(drivers_sorted.iloc[0]["vehicle_number"])
    podium_cars = set(drivers_sorted.iloc[:3]["vehicle_number"].astype(int))

    # Filter to valid events
    events_valid = events[events["track_distance"].notna()].copy()

    winner_distances = events_valid[events_valid["vehicle_number"] == winner_car][
        "track_distance"
    ]
    podium_distances = events_valid[events_valid["vehicle_number"].isin(podium_cars)][
        "track_distance"
    ]
    field_distances = events_valid[~events_valid["vehicle_number"].isin(podium_cars)][
        "track_distance"
    ]

    print("\nAverage track distance at brake onset:")
    print(f"  Winner: {winner_distances.mean():.1f}m")
    print(f"  Podium: {podium_distances.mean():.1f}m")
    print(f"  Field: {field_distances.mean():.1f}m")

    winner_vs_field = winner_distances.mean() - field_distances.mean()
    podium_vs_field = podium_distances.mean() - field_distances.mean()

    print("\nOverall tendency:")
    print(
        f"  Winner: {abs(winner_vs_field):.1f}m {'earlier' if winner_vs_field < 0 else 'later'} than field"
    )
    print(
        f"  Podium: {abs(podium_vs_field):.1f}m {'earlier' if podium_vs_field < 0 else 'later'} than field"
    )


def main():
    """Run brake timing analysis."""
    print("BRAKE TIMING ANALYSIS - WHEN DO FAST DRIVERS BRAKE?")
    print("=" * 80)

    # Load data
    drivers, events = load_data()

    # Analyze by zone
    timing_df = analyze_brake_timing_by_zone(drivers, events)

    # Overall pattern
    analyze_overall_brake_timing(drivers, events)

    # Save results
    output_path = Path(__file__).parent / "brake_timing_by_zone.csv"
    timing_df.to_csv(output_path, index=False)
    print(f"\n✓ Saved detailed brake timing analysis to: {output_path}")


if __name__ == "__main__":
    main()
