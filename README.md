# F1 Telemetry Explorer: Comparing Driver and Car Performance

A Streamlit app for comparing two Formula 1 drivers' fastest qualifying laps from the 2025 Italian Grand Prix, using official timing and telemetry data.

## Project Purpose

Formula 1 broadcasts show who was fastest, but rarely where on the lap or why. This project is for F1 fans and students who want to look past lap times but don't know how to work with raw car data.

**Primary question:** Where on the lap does one driver gain time over another in qualifying, and does that gain come from straight-line speed or corner speed?

**What the app does:** The user picks two drivers. The app then shows:

- their speed traces on a shared lap-distance axis (0–100% of the lap), with hover tooltips and zoom
- lap and sector times side by side
- the tire compound and tire age for each lap

## Repository Contents

| File | Description |
|---|---|
| `app.py` | Streamlit app |
| `analysis.ipynb` | Main analysis notebook: data loading, variable audit, data-quality checks, the two analytical questions, and the lap-alignment check |
| `f1_analysis.py` | Helper functions used by the analysis notebook |
| `requirements.txt` | Python dependencies |
| `AI_USE_DISCLOSURE.md` | AI-use disclosure |

## Data

**Source:** [FastF1](https://docs.fastf1.dev/) (v3.8), a Python library that wraps Formula 1's official live-timing feed.

**Session:** 2025 Italian Grand Prix, Qualifying (`fastf1.get_session(2025, "Italian Grand Prix", "Q")`).

**Observation unit:** One row is one telemetry sample from a driver's fastest qualifying lap: speed, throttle, brake, gear, DRS, RPM, X/Y position, and distance. Driver, team, lap time, and tire information (compound, tire age, new/used set) come from the laps table and are attached to each sample.

**Size:** About 12,000 telemetry rows × 25 columns (20 drivers, roughly 600 samples each), plus a laps table of 315 rows × 31 columns.

### Data Access

You don't need to download anything by hand, and no API key is required. On the first run, FastF1 downloads the session from the F1 live-timing API and caches it in a local `f1_cache/` folder. Later runs load from the cache.

- The first load needs an internet connection and can take a minute or two.
- `f1_cache/` is excluded from the repo (about 47 MB) and is recreated automatically.
- If you get a "cache directory does not exist" error, create the folder first with `mkdir f1_cache`.

## Setup and Run

Requires Python 3.10+.

```bash
# 1. Clone the repository
git clone https://github.com/harshsepi0l/f1-telemetry-explorer.git
cd f1-telemetry-explorer

# 2. (Optional) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the cache folder (first time only)
mkdir -p f1_cache

# 5. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

To reproduce the analysis, open the notebook with `jupyter notebook analysis.ipynb` and run all cells.

## Key Limitations

- **One session, one lap per driver.** The app is only 2025 Italian GP qualifying, and only each driver's fastest lap. Gaps can still come from setup, fuel load, or a tow, not just the car or the driver.
- **Irregular telemetry sampling.** Car data comes in about every 0.2–0.3 s. Corner minimums are approximate, and integrating speed over distance is a bad way to measure time gaps: integrated lap length differs by about 30 m between drivers. Official sector times are used instead.
- **Tires and DRS barely change here.** Every fastest lap was on Softs (19 of 20 on a fresh set) and every driver had DRS open for about 1.5 km. This session cannot show how tires or DRS affect performance. That needs race data.
- **Brake is on/off only.** The channel says whether the driver is braking, not how hard.
- **Descriptive, not causal.** The analysis cannot split the car from the driver. n = 20 and teammates share cars, so the grid correlations are just associations.
- **Untimed laps dropped.** Out/in laps have no lap time. I dropped them rather than filling them in.
- **Prototype.** The app runs locally and has not been deployed. Corner names on the speed chart are the next UX change. Race stints are the next data change.
