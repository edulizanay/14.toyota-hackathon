# Implementation Plan - Brake Point Drift Detector

## Overview

Incremental, feedback-driven implementation with validation gates at each step. Each step produces a visible output for review before proceeding.

---

## Final Repository Structure

```
14.toyota-hackathon/
├── context.md                         # Hackathon rules and track context
├── plan.md                           # Strategic plan and agreements
├── implementation-plan.md            # This document
├── demo-narration.md                 # 60-second demo script
├── data-structure.md                 # Raw data documentation
│
├── barber/                           # Original data files
│   ├── R1_barber_telemetry_data.csv  # Primary telemetry (1.5GB)
│   ├── 03_Provisional Results_Race 1_Anonymized.CSV  # USAC results
│   └── not-used/                     # Unused files (R2, weather, etc.)
│
├── data/                             # Processed data outputs
│   ├── telemetry-raw/                # Loaded R1 data only
│   │   └── all_drivers.csv           # Driver metadata
│   ├── brake-analysis/               # Brake event processing
│   │   ├── brake_events.csv          # All brake points with GPS (driver, lap, corner_id, lon, lat, timestamp, brake_type)
│   │   └── corner_definitions.json   # Manual polygon boundaries (C1-C17)
│   ├── gps-tracks/                   # Track visualization data
│   │   ├── track_centerline.csv      # Smoothed GPS trace
│   │   └── Barber-Motorsports-Park.png  # Reference track image
│   ├── consistency-scores/           # Analysis results
│   │   ├── dispersion_by_corner.csv  # Per driver, per corner std dev
│   │   └── driver_summary.csv        # Overall consistency rankings
│   └── visualizations/               # Generated plots
│       ├── step3_track_outline.html  # Plotly track plot
│       ├── step4_brake_overlay.html  # Brake points on track
│       ├── step5a_all_brakes.html    # All brake points visualization
│       ├── step5c_corner_zones.html  # Color-coded corners
│       ├── step7_correlation.png     # Lap time vs dispersion scatter plot
│       ├── step8_reference_driver.html  # Gray reference clusters
│       └── final_interactive.html    # Complete demo viz
│
├── src/                              # Source code
│   ├── data_loaders.py               # Load & pivot telemetry, load USAC
│   ├── brake_detection.py            # Percentile threshold & brake events
│   ├── track_rendering.py            # GPS smoothing & track plotting
│   ├── corner_detection.py           # Polygon definitions & assignment
│   ├── consistency_analysis.py       # Std dev calculation & validation
│   └── visualization.py              # Interactive Plotly dashboard
│
├── notebooks/                        # Exploration (optional)
│   └── data_exploration.ipynb        # Initial data checks
│
└── submission_description.md         # Hackathon submission writeup
```


YOU MUST NOT VIOLATE THIS STRUCTURE, if during your progress you realize we need an additional file or some existing file should be elsewhere, you must stop and ask Edu first.



## Data Requirements

**Files We Need:**

1. **R1_barber_telemetry_data.csv** (1.5GB) - Primary data source
   - Extract from telemetry_name/telemetry_value pairs:
     - `VBOX_Long_Minutes` - GPS longitude (for track & brake locations)
     - `VBOX_Lat_Min` - GPS latitude (for track & brake locations)
     - `pbrake_f` - Front brake pressure (to detect brake events)
     - `pbrake_r` - Rear brake pressure (to detect brake events)
     - `speed` - Vehicle speed (for corner detection via speed minima)
     - `timestamp` - To correlate all parameters
     - `lap` - To group by lap
     - `vehicle_number` - To identify drivers

2. **03_Provisional Results_Race 1_Anonymized.CSV** (2.4KB) - Fastest driver identification
   - Extract:
     - `NUMBER` - Driver/car number
     - `FL_TIME` - Fastest lap time (to identify reference driver)

**Files We Probably Don't Need** (move to `/barber/not-used/` to stay focused):
- **R2 data** - All R2 files (using R1 only per agreements)
- **Weather files** - `26_Weather_Race 1_Anonymized.CSV` (not needed for brake consistency)
- **Pit stop timing** - Not needed for MVP
- **Sector analysis** - `23_AnalysisEnduranceWithSections_Race 1_Anonymized.CSV` (creating our own corner definitions)

**Files to Keep Available** (might need for validation):
- **Lap start/end files** - Backup if lap numbers in telemetry are corrupted (known issue per context.md)
- **Results by class** - May help identify Pro vs Am if needed for analysis

---

## Phase 1: Foundation & Setup

### Step 1: Project Setup ✅ COMPLETED
**Goal**: Organize workspace and prepare data infrastructure

**Tasks**:
- [x] Create folder structure (see "Final Repository Structure" above):
  - [x] `data/` with subfolders: telemetry-raw, brake-analysis, gps-tracks, consistency-scores, visualizations
  - [x] `src/` for Python modules
  - [x] `barber/not-used/` for archived files
- [x] Move unused files to `barber/not-used/` (R2, weather, pit stops, sector analysis)
- [x] Install required packages: `pandas`, `plotly`, `scipy`, `numpy`, `pyproj` (for GPS to meters conversion)
- [x] Initialize private GitHub repository

**Files Created**: `.gitignore`, `requirements.txt`, `scratchpad.md`

**Deliverable**: Clean folder structure matching final layout, working Python environment

---

### Step 2: Data Loading & Transformation ✅ COMPLETED
**Goal**: Load and transform data files into usable format

**Problem**:
- Telemetry files (1.5GB) are in LONG FORMAT - one row per parameter per timestamp, must process carefully
- File contains 100+ telemetry parameters but we only need 8
- Pivoting entire file to wide format risks OOM (could balloon to 10GB+)
- GPS coordinates are in degrees (lon/lat) but dispersion calculations need meters
- USAC timing files use semicolon delimiter

**Tasks**:
- [x] Write `src/data_loaders.py` with functions: `load_telemetry()`, `load_usac_results()`
- [x] Read telemetry CSV in chunks (500k rows at a time using pandas chunksize)
- [x] Filter each chunk to only needed telemetry_names: `pbrake_f`, `pbrake_r`, `VBOX_Long_Minutes`, `VBOX_Lat_Min`, `speed`
- [x] Convert filtered chunks from long to wide format (pivot_table per chunk)
- [x] Append processed chunks to create filtered dataset
- [x] Convert GPS coordinates (lon/lat degrees) to local Cartesian (x, y) meters using UTM projection (EPSG:32616)
- [x] Add columns: `x_meters`, `y_meters` for all subsequent calculations
- [x] Calculate P95 threshold from combined brake pressure values (42.84 bar)
- [x] Verify all required columns exist: `pbrake_f`, `pbrake_r`, `VBOX_Long_Minutes`, `VBOX_Lat_Min`, `x_meters`, `y_meters`, `speed`, `timestamp`, `lap`, `vehicle_number`
- [x] Save to `data/telemetry-raw/all_drivers.csv` (114.3 MB)

**Files Created**:
- `src/data_loaders.py` - Data loading utilities
- `src/load_and_process.py` - Pipeline execution script
- `data/telemetry-raw/all_drivers.csv` - 1,043,276 rows from 20 vehicles with GPS and meters

**Results**: Processed 1.5GB → 114.3 MB, 20 vehicles, fastest driver car #13 (1:37.428)

**🛑 Checkpoint**: ✅ Data loaded successfully with all required columns

---

## Phase 2: Track Visualization

### Step 3: Generate Track Outline
**Goal**: Create visual representation of Barber track from GPS data

**Tasks**:
- [ ] Write `src/track_rendering.py` with function `generate_track_outline()`
- [ ] Load R1 telemetry GPS coordinates (`VBOX_Long_Minutes`, `VBOX_Lat_Min`)
- [ ] Extract one clean lap of GPS points (fastest lap)
- [ ] Plot GPS trace as line using Plotly
- [ ] Apply smoothing: scipy `UnivariateSpline` with s=0.001 (light, preserves shape)
- [ ] Add dark theme styling
- [ ] Save to `data/visualizations/step3_track_outline.html`
- [ ] Show to Edu (open HTML file in browser) and iterate on smoothing/lap averaging until track looks good

**Files Created**:
- `src/track_rendering.py` - Track visualization utilities
- `data/gps-tracks/track_centerline.csv` - Smoothed GPS trace
- `data/visualizations/step3_track_outline.html` - Interactive track plot

**🛑 Checkpoint: Get feedback from Edu on track appearance**

---

## Phase 3: Brake Point Visualization

### Step 4: Plot All Brakes for Single Driver, Single Lap
**Goal**: Validate brake detection and GPS correlation

**Tasks**:
- [ ] Write `src/brake_detection.py` with function `detect_brake_events()`
- [ ] Select one driver, one clean lap
- [ ] Apply P95 threshold: brake event when `pbrake_f > P95` OR `pbrake_r > P95`
- [ ] Get GPS coordinates at each brake timestamp
- [ ] Overlay brake points as colored dots on track from Step 3
- [ ] Save to `data/visualizations/step4_brake_overlay.html`
- [ ] Show to Edu (open HTML file in browser) - should see ~17 distinct brake clusters + pit lane brakes
- [ ] If too many scattered points or missing zones, adjust percentile (try P96, P94, etc.) and iterate until Edu approves

**Files Created**:
- `src/brake_detection.py` - Brake event detection utilities
- `data/visualizations/step4_brake_overlay.html` - Track with brake points

**🛑 Checkpoint: Get feedback from Edu - do brake points look reasonable?**

---

## Phase 4: Corner Detection & Filtering

### Step 5: Define & Detect Curvature Zones
**Goal**: Group brake points into corners, filter out non-corner braking

**Approach - Visual + Manual Polygon Definition**:

**Step 5a: Plot all brake points first**
- [ ] Write `src/corner_detection.py` with functions `plot_all_brakes()`, `define_corners()`, `assign_to_corners()`
- [ ] Visualize ALL brake events from all drivers on track map
- [ ] Save to `data/visualizations/step5a_all_brakes.html`
- [ ] Show to Edu (open HTML in browser) - identify pit lane visually (off racing line, see barber-motorsports-Park.png)

**Step 5b: Define corner polygons manually**
- [ ] Based on visual brake clusters from Step 5a, manually define ~17 polygons in code
- [ ] Use simple coordinate bounds in meters: `[(min_x, max_x), (min_y, max_y)]` per corner
- [ ] Exclude pit lane area completely
- [ ] Save to `data/brake-analysis/corner_definitions.json`: `C1: {x_min, x_max, y_min, y_max, ...}` (in meters)

**Step 5c: Assign brake points to corners**
- [ ] For each brake point: check which corner polygon it falls within
- [ ] Label with corner ID (C1, C2, etc.)
- [ ] Discard any brake points not in corner polygons (pit lane, straights)
- [ ] Save visualization to `data/visualizations/step5c_corner_zones.html` (color-coded by corner)
- [ ] Show to Edu (open HTML) and iterate on polygon boundaries until all corners captured correctly

**Files Created**:
- `src/corner_detection.py` - Corner polygon definition and assignment
- `data/brake-analysis/corner_definitions.json` - Manual polygon boundaries (C1-C17) in meters (x, y)
- `data/visualizations/step5a_all_brakes.html` - All brake points visualization
- `data/visualizations/step5c_corner_zones.html` - Color-coded corner zones

**🛑 Checkpoint: Get feedback from Edu - are corners correctly identified?**

---

### Step 6: Handle Multiple Brakes Per Corner
**Goal**: Use first brake application per corner per lap

**Strategy**:
- Per corner, per lap: use **first brake event** (earliest timestamp) that falls within that corner's polygon
- Captures brake initiation point (when driver starts braking for that corner)
- Works naturally for both front and rear brakes (whichever crosses P95 threshold first)
- Ignore subsequent brakes in same corner on same lap (trail braking, corrections)

**Tasks**:
- [ ] For each (driver, lap, corner): identify first brake event by timestamp
- [ ] Store: driver, lap, corner_id, GPS (lon, lat), coordinates (x_meters, y_meters), timestamp, brake_type
- [ ] Save to `data/brake-analysis/brake_events.csv`
- [ ] Print sample to verify one point per (driver, lap, corner) combination

**Files Created**:
- `data/brake-analysis/brake_events.csv` - One brake point per corner per lap per driver

**🛑 Checkpoint: Verify one point per corner per lap (print counts to console)**

---

## Phase 5: Consistency Analysis

### Step 7: Calculate Dispersion & Validate Assumptions
**Goal**: Compute std dev for brake points, test core hypothesis

**Tasks**:
- [ ] Write `src/consistency_analysis.py` with function `calculate_dispersion()`
- [ ] For each corner, for each driver: calculate std dev of brake point coordinates using x_meters and y_meters
- [ ] Calculate Euclidean distance std dev: sqrt((std_dev_x)^2 + (std_dev_y)^2) for each corner
- [ ] Calculate average dispersion across all corners per driver
- [ ] Load lap times from USAC results
- [ ] Create table: driver | avg_lap_time | avg_dispersion_meters
- [ ] Save to `data/consistency-scores/dispersion_by_corner.csv` (per driver, per corner)
- [ ] Save to `data/consistency-scores/driver_summary.csv` (overall per driver)
- [ ] Sort driver_summary by avg_lap_time and print to console
- [ ] **Critical validation**: Does fastest driver have lowest dispersion? If no: 🛑 STOP and consult Edu
- [ ] Create scatter plot: x=avg_lap_time, y=avg_dispersion_meters, one point per driver
- [ ] Save to `data/visualizations/step7_correlation.png`

**Files Created**:
- `src/consistency_analysis.py` - Dispersion calculation utilities
- `data/consistency-scores/dispersion_by_corner.csv` - Per driver, per corner std dev
- `data/consistency-scores/driver_summary.csv` - Overall consistency rankings (driver | avg_lap_time | avg_dispersion_meters)
- `data/visualizations/step7_correlation.png` - Scatter plot showing lap time vs dispersion correlation

**🛑 Checkpoint: Confirm hypothesis holds before visualizing (check console output)**

---

## Phase 6: Reference Visualization

### Step 8: Display Fastest Driver (Gray Reference Dots)
**Goal**: Show "ideal" brake point clusters as reference

**Tasks**:
- [ ] Write `src/visualization.py` with function `plot_reference_driver()`
- [ ] Identify fastest driver (lowest avg lap time from USAC data)
- [ ] Plot their brake points in semi-transparent gray (#808080, alpha=0.5)
- [ ] Overlay corner badges (C1, C2, ... C17) at cluster centroids
- [ ] Display dispersion as dots (simplest)
- [ ] Dark background (#0a0a0a), gray dots with white outline, corner labels in white text
- [ ] Save to `data/visualizations/step8_reference_driver.html`
- [ ] Show to Edu (open HTML) and iterate on styling/clarity until approved

**Files Created**:
- `src/visualization.py` - Interactive visualization utilities
- `data/visualizations/step8_reference_driver.html` - Track with gray reference clusters

**🛑 Checkpoint: Get feedback from Edu on reference visualization**

---

## Phase 7: Interactive Driver Comparison

### Step 9: Add Driver Selection & Comparison View
**Goal**: Allow comparison of any driver against reference

**Tasks**:
- [ ] Extend `src/visualization.py` with function `create_interactive_dashboard()`
- [ ] Create dropdown menu with all driver IDs/numbers
- [ ] On selection: plot selected driver's brake points in color (green→red by dispersion percentile)
- [ ] Keep gray reference visible underneath
- [ ] Right panel: table with Corner ID | Dispersion (m)
- [ ] Enable Plotly's native zoom/pan
- [ ] Add hover tooltips: Corner name, dispersion value, lap number
- [ ] Color mapping: Green (<25th percentile) → yellow (50th) → red (>75th)
- [ ] Save to `data/visualizations/final_interactive.html`
- [ ] Show to Edu (open HTML) and iterate on UX/styling until approved for demo

**Files Created**:
- `data/visualizations/final_interactive.html` - Complete interactive demo visualization

**🛑 Checkpoint: Get feedback from Edu on full UX flow**

---

## Phase 8: Polish & Prep for Demo

### Step 10: Demo Preparation
**Tasks**:
- [ ] Optimize performance in `final_interactive.html` (pre-compute dispersion, cache track outline)
- [ ] Ensure HTML file works standalone (no external dependencies)
- [ ] Write `submission_description.md` for hackathon judges

**Files Created**:
- `submission_description.md` - Hackathon submission writeup

**Final Deliverable**: Working prototype (`data/visualizations/final_interactive.html`) + submission writeup

---

## Implementation Decisions (Finalized)

**Brake Detection**:
- ✅ Threshold: P95 (95th percentile) - top 5% of brake pressure
- ✅ Logic: `pbrake_f > P95` OR `pbrake_r > P95` (filter in pipeline, don't merge columns)
- ✅ First brake wins: Use earliest timestamp within corner polygon

**Corner Detection**:
- ✅ Manual polygon definition based on visual brake clusters
- ✅ ~17 polygons for Barber corners, exclude pit lane

**Track Rendering**:
- ✅ Start with single fastest lap GPS trace
- ✅ Smoothing: scipy UnivariateSpline (s=0.001)

**Visualization**:
- ✅ Simple dots for dispersion (no convex hulls for MVP)
- ✅ Color scale: percentile-based (green/yellow/red)

**Critical Validations**:
- ❓ Does P95 threshold give us ~17 clear corner clusters? (Step 4)
- ❓ Does fastest lap time correlate with lowest dispersion? (Step 7 - CRITICAL)
- ❓ Do manual polygons capture all corner braking correctly? (Step 5)

---

## Notes

- **Incremental approach**: Each step has a feedback gate - don't proceed until approved
- **Data first**: Check assumptions in actual data before implementing complex logic
- **Fail fast**: If Step 7 validation fails, reassess entire approach
- **Keep it simple**: Start with simplest solution at each step, add complexity only if needed
