# Traction Efficiency Analysis

## Goal

Detect: **Too conservative?** (leaving time) | **Too aggressive?** (wheelspin/sliding) | **Optimal?** (using grip efficiently)

---

## Physics

Cars have finite grip: `total_G = sqrt(accx² + accy²)` (friction circle), they can use it to brake/accelerate AND/OR turn.

**Traction Envelope:** Max total grip each driver achieved at different lateral loads (how hard they're cornering). It's the efficient frontier of grip usage.

**Note:** `accy = velocity² / turn_radius` (implicitly contains angle + speed)
---

## Three Metrics

**1. Grip Utilization (%):** How close the driver pushes to maximum grip (`actual_G / envelope_max`) in a given zone

**2. Over-Limit Events (#):** Count of aggressive driving errors
- Throttle↑ but accx↓ (wheelspin),
- Steering↑ but accy plateau (understeer),
- Accy spike + accx↓ (oversteer)

**3. Time Lost per Zone (s):** How much faster the zone could be with full grip utilization (conservative & aggressive driving)

---

## How to Build It

### Step 0: Auto-Detect Turn Zones
- Filter samples where `|accy| is above a percentile X` (real turning, not straights)
- Cluster by track distance (`Laptrigger_lapdist_dls`) using DBSCAN
- For each cluster: find 95% boundaries (2.5th to 97.5th percentile of track distance)
- This defines turn zones automatically from data (eliminates steering corrections on straights)

### Step 1: Build Envelope (per driver, per zone)
- Calculate `total_G = sqrt(accx² + accy²)` for all samples
- Bin by `accy` (lateral G)
- Find max `total_G` in each bin
- Connect = envelope curve

### Step 2: Calculate Utilization
- For each sample: `utilization = total_G / envelope_max`
- Track average per zone/lap

### Step 3: Detect Events

**Note:** Use rolling averages (3-5 samples) to detect trends, not single-point deltas.

**Then detect:**
- **Wheelspin:** If throttle_trend > +X% AND accx_trend < -Y% → mark event
- **Understeer:** If steering_trend > +X% AND accy_trend ≈ 0% → mark event
- **Oversteer:** If accy spikes AND accx_trend < -0.05g → mark event

**Group consecutive detections into single events, then count per driver/zone.**

### Step 4: Summarize
- Per driver/zone/lap: avg utilization %, event counts, time lost estimate

**Lap Classification (per driver, per lap, per zone):**
```
If over_limit_events > 0:
  → "Aggressive" (mistakes detected)
Else if avg_utilization < 95%:
  → "Conservative" (leaving time on table)
Else:
  → "Optimal" (95-100% utilization, no mistakes)
```

**Time Lost Estimation (per driver, per lap, per zone):**
1. `zone_duration = zone_distance / avg_speed`
2. `ΔV = avg_grip_deficit × zone_duration`
3. `time_lost = zone_distance/avg_speed - zone_distance/(avg_speed + ΔV)`

---

## Visualizations

**Technology Stack:**
- Backend: Python (data processing, envelope calculation, export JSON)
- Track View: Keep existing Plotly implementation (minor updates to colors/data)
- Analytics View: React/Vue with D3.js for charts

**Tab 1: Track View (Plotly - existing)**
- **Track map:** GPS-positioned samples using existing Plotly track visualization
- **Updates needed:** Change point colors to green/yellow/red based on classification
- **Toggle modes:**
  - Mode A: Individual samples with time lost labels
  - Mode B: Zone centroids with cumulative time lost per zone

**Tab 2: Analytics View (React + D3.js - new)**
- **Left panel:** Summary table (utilization %, event counts, time lost per driver/zone)
  - Implementation: AG Grid or TanStack Table
- **Right panel:** Traction envelope hexbin heatmap
  - X-axis: accx (longitudinal G), Y-axis: |accy| (lateral G)
  - Hexbin color: Frequency (darker = more samples at that G-force combination)
  - Overlay: Envelope boundary line + over-limit event markers
  - Implementation: D3.js hexbin