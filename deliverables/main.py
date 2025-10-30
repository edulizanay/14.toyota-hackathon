# Entry point placeholder — no executable code.
# Purpose: Orchestrate data processing and visuals to produce the final v2 HTML.

# Expected CLI args (example):
# --telemetry_csv deliverables/data/input/telemetry.csv
# --usac_csv deliverables/data/input/usac.csv
# --zones_json deliverables/data/input/corner_definitions.json
# --outdir deliverables/data/output
# [--force]

# Sequence (using deliverables/src modules):
#   from deliverables.src import data_processing as dp
#   from deliverables.src import visuals as viz
#
# 1) Data processing
#    df = dp.load_and_pivot_telemetry(telemetry_csv)
#    threshold = dp.compute_brake_threshold_p5(df)
#    events = dp.detect_brake_onsets(df, threshold)
#    events_race = dp.filter_racing_laps(events, df)
#    # Build/reuse centerline (saved under data/output/track_centerline.csv)
#    viz.build_track_outline_figure(df)
#    events_zoned = dp.assign_brake_events_to_zones(
#        events_race,
#        centerline_x, centerline_y,  # Derived from saved centerline CSV or return from build call
#        zones_json
#    )
#    disp = dp.compute_zone_dispersion(events_zoned)
#    summary = dp.summarize_driver_consistency(disp)
#    summary = dp.merge_usac_lap_times(summary, usac_csv)
#
# 2) Visuals
#    viz.render_zone_focus_dashboard(
#        telemetry_df=df,
#        brake_events_df=events_zoned,
#        driver_summary_df=summary,
#        reference_vehicle_number=<fastest from summary>,
#        output_path=<outdir>/dashboard.html,
#    )
