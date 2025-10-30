# ABOUTME: Entry point orchestrator for brake point analysis pipeline
# ABOUTME: Runs data processing and visualization to produce zone-focused dashboard HTML

import argparse
from pathlib import Path
from src import data_processing as dp
from src import visuals as viz


def main():
    """
    Main entry point for the deliverables pipeline.
    Orchestrates data processing and visualization to produce dashboard.html.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate zone-focused brake analysis dashboard from telemetry data"
    )
    parser.add_argument(
        "--telemetry_csv",
        type=str,
        default="data/input/telemetry.csv",
        help="Path to telemetry CSV file (default: data/input/telemetry.csv)",
    )
    parser.add_argument(
        "--usac_csv",
        type=str,
        default="data/input/usac.csv",
        help="Path to USAC results CSV file (default: data/input/usac.csv)",
    )
    parser.add_argument(
        "--zones_json",
        type=str,
        default="data/input/corner_definitions.json",
        help="Path to corner definitions JSON (default: data/input/corner_definitions.json)",
    )
    parser.add_argument(
        "--corner_labels_json",
        type=str,
        default="data/input/corner_labels.json",
        help="Path to corner labels JSON (optional, default: data/input/corner_labels.json)",
    )
    parser.add_argument(
        "--pit_lane_json",
        type=str,
        default="data/input/pit_lane.json",
        help="Path to pit lane JSON (optional, default: data/input/pit_lane.json)",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="data/output",
        help="Output directory for results (default: data/output)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regenerate centerline even if it exists",
    )

    args = parser.parse_args()

    # Convert to Path objects
    telemetry_csv = Path(args.telemetry_csv)
    usac_csv = Path(args.usac_csv)
    zones_json = Path(args.zones_json)
    corner_labels_json = Path(args.corner_labels_json)
    pit_lane_json = Path(args.pit_lane_json)
    outdir = Path(args.outdir)

    # Create output directory
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("BARBER MOTORSPORTS PARK - BRAKE ANALYSIS PIPELINE")
    print("=" * 80)
    print()

    # ========================================================================
    # Phase 1: Data Processing
    # ========================================================================
    print("PHASE 1: DATA PROCESSING")
    print("-" * 80)
    print()

    # 1) Load and pivot telemetry
    print("Step 1: Loading telemetry data...")
    print("-" * 80)
    df = dp.load_and_pivot_telemetry(telemetry_csv)
    print()

    # 2) Compute brake threshold
    print("Step 2: Computing brake pressure threshold...")
    print("-" * 80)
    threshold = dp.compute_brake_threshold_p5(df)
    print()

    # 3) Detect brake onset events
    print("Step 3: Detecting brake onset events...")
    print("-" * 80)
    events = dp.detect_brake_onsets(df, threshold)
    print()

    # 4) Filter to racing laps only
    print("Step 4: Filtering to racing laps...")
    print("-" * 80)
    events_race = dp.filter_racing_laps(events, df)
    print()

    # 5) Build/load track centerline
    print("Step 5: Building track centerline...")
    print("-" * 80)
    centerline_csv = outdir / "track_centerline.csv"

    if centerline_csv.exists() and not args.force:
        print(f"Loading existing centerline from {centerline_csv}")
        centerline_x, centerline_y = viz.load_centerline(centerline_csv)
    else:
        print("Generating new centerline...")
        centerline_x, centerline_y = viz.compute_centerline(
            df,
            vehicle_number=None,
            lap_number=None,
        )
        viz.save_centerline(centerline_x, centerline_y, centerline_csv)
    print()

    # 6) Assign brake events to zones
    print("Step 6: Assigning brake events to zones...")
    print("-" * 80)
    events_zoned = dp.assign_brake_events_to_zones(
        events_race, centerline_x, centerline_y, zones_json
    )
    print(f"✓ Assigned {(events_zoned['zone_id'].notna()).sum():,} events to zones")
    print()

    # 7) Compute zone dispersion
    print("Step 7: Computing brake point dispersion by zone...")
    print("-" * 80)
    disp = dp.compute_zone_dispersion(events_zoned)
    print(f"✓ Computed dispersion for {len(disp)} driver-zone combinations")
    print()

    # 8) Summarize driver consistency
    print("Step 8: Summarizing driver consistency...")
    print("-" * 80)
    summary = dp.summarize_driver_consistency(disp)
    print(f"✓ Summarized {len(summary)} drivers")
    print()

    # 9) Merge USAC lap times
    print("Step 9: Merging USAC lap times...")
    print("-" * 80)
    summary = dp.merge_usac_lap_times(summary, usac_csv)
    print(f"✓ Merged lap times for {summary['fastest_lap_time'].notna().sum()} drivers")
    print()

    # 10) Save intermediate CSVs
    print("Step 10: Saving intermediate results...")
    print("-" * 80)

    # Save all drivers telemetry subset (optional, for reference)
    df.to_csv(outdir / "all_drivers.csv", index=False)
    print(f"✓ Saved all_drivers.csv ({len(df):,} rows)")

    # Save brake events
    events_zoned.to_csv(outdir / "brake_events.csv", index=False)
    print(f"✓ Saved brake_events.csv ({len(events_zoned):,} events)")

    # Save driver summary
    summary.to_csv(outdir / "driver_summary.csv", index=False)
    print(f"✓ Saved driver_summary.csv ({len(summary)} drivers)")
    print()

    # ========================================================================
    # Phase 2: Visualization
    # ========================================================================
    print("PHASE 2: VISUALIZATION")
    print("-" * 80)
    print()

    # Determine reference driver (fastest lap time)
    reference_vehicle_number = summary.loc[
        summary["fastest_lap_seconds"].idxmin(), "vehicle_number"
    ]
    print(f"Reference driver (fastest lap): #{int(reference_vehicle_number)}")
    print()

    # Build dashboard
    print("Step 11: Rendering zone-focused dashboard...")
    print("-" * 80)
    dashboard_path = Path("dashboard.html")  # Output in same directory as main.py

    viz.render_zone_focus_dashboard(
        telemetry_df=df,
        brake_events_df=events_zoned,
        driver_summary_df=summary,
        reference_vehicle_number=int(reference_vehicle_number),
        output_path=dashboard_path,
        centerline_csv_path=centerline_csv,
        corner_definitions_json=zones_json,
        corner_labels_json=corner_labels_json if corner_labels_json.exists() else None,
        pit_lane_json=pit_lane_json if pit_lane_json.exists() else None,
    )
    print()

    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print()
    print("Output files:")
    print(f"  • {outdir / 'all_drivers.csv'}")
    print(f"  • {outdir / 'brake_events.csv'}")
    print(f"  • {outdir / 'driver_summary.csv'}")
    print(f"  • {outdir / 'track_centerline.csv'}")
    print(f"  • {dashboard_path} (main dashboard)")
    print()
    print(
        f"✓ Open {dashboard_path.absolute()} in a web browser to view the interactive dashboard"
    )
    print()


if __name__ == "__main__":
    main()
