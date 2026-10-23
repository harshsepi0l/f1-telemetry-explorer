# F1 Telemetry Explorer: Comparing Driver and Car Performance

A Streamlit app for comparing two Formula 1 drivers' fastest qualifying laps from the 2025 Italian Grand Prix, using official timing and telemetry data.

## Project Purpose

Formula 1 broadcasts show who was fastest, but rarely where on the lap or why. This project is for F1 fans and students who want to look past lap times but don't know how to work with raw car data.

**Primary question:** Where on the lap does one driver gain time over another in qualifying, and does that gain come from straight-line speed or corner speed?

**What the app does:** The user picks two drivers. The app then shows:

- both fastest laps on the Monza layout, with play, pause, a scrubber, DRS zones, and numbered corners
- a speed chart on lap percent (0–100). The dots follow the cars. Hover for both drivers, or click to jump
- lap time and the three sector times side by side
- team color and lap time on each driver card. Teammates share a color, so the second driver is a lighter shade

Tire compound is not shown in the app. It barely changes in this session, so it is only in the analysis.

## Repository Contents

| File | Description |
|---|---|
| `app.py` | Streamlit app. Loads the session and passes the two laps into `race.html` |
| `race.html` | Race view and speed chart. `app.py` fills in `__DATA__` before showing it |
| `f1_cache/2025/` | Parsed 2025 Italian GP qualifying cache, so the app does not have to call the F1 API |
| `analysis.ipynb` | Main analysis notebook: data loading, variable audit, data-quality checks, the two analytical questions, and the lap-alignment check |
| `f1_analysis.py` | Helper functions used by the analysis notebook |
| `requirements.txt` | Python dependencies. FastF1 is pinned to 3.8.3 so it matches that cache |
| `AI_USE_DISCLOSURE.md` | AI-use disclosure |

## Data

**Source:** [FastF1](https://docs.fastf1.dev/) 3.8.3, a Python library that wraps Formula 1's official live-timing feed.

**Session:** 2025 Italian Grand Prix, Qualifying (`fastf1.get_session(2025, "Italian Grand Prix", "Q")`).

**Observation unit:** One row is one telemetry sample from a driver's fastest qualifying lap: speed, throttle, brake, gear, DRS, RPM, X/Y position, and distance. Driver, team, lap time, and tire information (compound, tire age, new/used set) come from the laps table and are attached to each sample.

**Size:** About 12,000 telemetry rows × 25 columns (20 drivers, roughly 600 samples each), plus a laps table of 315 rows × 31 columns.

### Data Access

You don't need to download anything by hand, and no API key is required. The parsed qualifying files are already in `f1_cache/2025/`, so a normal run loads from those files.

- The F1 live-timing site often blocks cloud servers. That is why the parsed cache is in the repo.
- Only the local HTTP cache (`f1_cache/*.sqlite`) is gitignored. FastF1 rebuilds it if it needs to.
- If those `.ff1pkl` files are missing, FastF1 will try to download the session. That needs an internet connection and can take a minute or two.

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

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Run the commands above from inside `f1-telemetry-explorer`. The cache and `race.html` sit next to `app.py`.

In the terminal you should see `Using cached data` and then `Finished loading data for 20 drivers`. That means it used the files in the repo and did not download the session. The first load still takes a few seconds because the telemetry files are large.

If the terminal says `No cached data found` or `Failed to load`:

- You started Streamlit from a different folder, or `f1_cache/2025/` did not come down with the clone.
- Do not replace `f1_cache/` with an empty folder. That makes FastF1 try the F1 website, which often fails.

The page should show two driver dropdowns. Pick two different drivers. The race view is under **Race around Monza**, and the lap and sector times are under that. Corner numbers come from a small extra lookup. If that lookup fails, the race and the speed chart still run.

To reproduce the analysis, stay in the same folder and run `jupyter notebook analysis.ipynb`, then run all cells. The notebook uses the same cache.

## Key Limitations

- **One session, one lap per driver.** The app is only 2025 Italian GP qualifying, and only each driver's fastest lap. Gaps can still come from setup, fuel load, or a tow, not just the car or the driver.
- **Irregular telemetry sampling.** Car data comes in about every 0.2–0.3 s. Corner minimums are approximate, and integrating speed over distance is a bad way to measure time gaps: integrated lap length differs by about 30 m between drivers. Official sector times are used instead.
- **Tires and DRS barely change here.** Every fastest lap was on Softs (19 of 20 on a fresh set) and every driver had DRS open for about 1.5 km. This session cannot show how tires or DRS affect performance. That needs race data.
- **Brake is on/off only.** The channel says whether the driver is braking, not how hard.
- **Descriptive, not causal.** The analysis cannot split the car from the driver. n = 20 and teammates share cars, so the grid correlations are just associations.
- **Untimed laps dropped.** Out/in laps have no lap time. I dropped them rather than filling them in.
- **Corners are on the map.** The next data change is race stints, where tire compound, tire age, and DRS actually change.
