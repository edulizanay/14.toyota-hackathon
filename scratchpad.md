# Scratchpad - Brake Point Drift Detector

## Session Log

### 2025-10-29 - Phase 1: Step 1 - Project Setup

**Completed:**
-  Created folder structure:
  - `data/` with subfolders: telemetry-raw, brake-analysis, gps-tracks, consistency-scores, visualizations
  - `src/` for Python modules
  - `barber/not-used/` for archived files
-  Moved unused files to `barber/not-used/`:
  - All R2 telemetry and lap files (R2_barber_*.csv)
  - All R2 results files (Race 2 related CSVs)
  - Weather files (26_Weather_*.CSV)
  - Sector analysis files (23_AnalysisEnduranceWithSections_*.CSV)
  - R2 best laps file
-  Installed required Python packages in virtual environment:
  - pandas 2.3.3
  - plotly 6.3.1
  - scipy 1.16.3
  - numpy 2.3.4
  - pyproj 3.7.2
-  Initialized git repository
-  Created .gitignore (excludes venv, large CSVs, OS files)

**Files Kept in barber/ (per plan):**
- `R1_barber_telemetry_data.csv` (1.5GB) - primary data source
- `R1_barber_lap_end.csv`, `R1_barber_lap_start.csv`, `R1_barber_lap_time.csv` - backup for lap validation
- `03_Provisional Results_Race 1_Anonymized.CSV` - needed for fastest driver identification
- `05_Provisional Results by Class_Race 1_Anonymized.CSV` - may need for Pro vs Am
- `05_Results by Class GR Cup Race 1 Official_Anonymized.CSV` - available if needed
- `99_Best 10 Laps By Driver_Race 1_Anonymized.CSV` - available if needed

**Environment Setup:**
- Python 3.13.0
- Virtual environment: `/venv/` (use `source venv/bin/activate` before running scripts)

**Next Steps:**
- Phase 1: Step 2 - Data Loading & Transformation
- Need to process 1.5GB telemetry file in chunks
- Filter to only needed parameters: pbrake_f, pbrake_r, VBOX_Long_Minutes, VBOX_Lat_Min, speed, timestamp, lap, vehicle_number
- Convert GPS coordinates to meters using UTM projection (pyproj)

**Technical Notes:**
- Telemetry file is in LONG FORMAT (one row per parameter per timestamp)
- Must process in chunks to avoid OOM (10k-100k rows at a time)
- USAC timing files use semicolon delimiter, telemetry uses comma
