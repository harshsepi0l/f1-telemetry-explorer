import os

import fastf1
import numpy as np
import pandas as pd

CACHE_DIR = "f1_cache"

CORNER_NAMES = {1: "T1 chicane", 4: "Roggia", 6: "Lesmo 1", 7: "Lesmo 2", 8: "Ascari", 11: "Parabolica"}


def load_session(year=2025, event="Italian Grand Prix", kind="Q"):
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.set_log_level("ERROR")
    fastf1.Cache.enable_cache(CACHE_DIR)
    session = fastf1.get_session(year, event, kind)
    session.load(weather=False, messages=False)
    return session


def get_laps(session):
    return session.laps.rename(columns={"TyreLife": "TireLife", "FreshTyre": "FreshTire"})


def build_telemetry(laps):
    all_tel = []
    for driver in laps["Driver"].unique():
        fastest = laps.pick_drivers(driver).pick_fastest()
        t = fastest.get_telemetry()
        t["Driver"] = driver
        t["Team"] = fastest["Team"]
        t["LapTime_s"] = fastest["LapTime"].total_seconds()
        t["Compound"] = fastest["Compound"]
        t["TireLife"] = fastest["TireLife"]
        t["FreshTire"] = fastest["FreshTire"]
        t["LapFrac"] = t["Distance"] / t["Distance"].max()
        all_tel.append(t)
    return pd.concat(all_tel, ignore_index=True)


def key_corners(session, lap_length):
    corners = session.get_circuit_info().corners.copy()
    corners["Frac"] = corners["Distance"] / lap_length
    corners = corners[corners["Number"].isin(CORNER_NAMES.keys())].copy()
    corners["Name"] = corners["Number"].map(CORNER_NAMES)
    return corners


def min_speed_near(t, frac, window=0.02):
    near = t[(t["LapFrac"] >= frac - window) & (t["LapFrac"] <= frac + window)]
    return near["Speed"].min()


def speed_on_grid(t, n=2000):
    x = np.linspace(0, 1, n)
    return x, np.interp(x, t["LapFrac"], t["Speed"])


def drs_open_distance(t):
    # DRS codes 10, 12 and 14 mean the flap is open
    step = t["Distance"].diff().fillna(0)
    return step[t["DRS"] >= 10].sum()


def lap_summary(lap):
    return pd.Series({
        "Lap time": lap["LapTime"].total_seconds(),
        "Sector 1": lap["Sector1Time"].total_seconds(),
        "Sector 2": lap["Sector2Time"].total_seconds(),
        "Sector 3": lap["Sector3Time"].total_seconds(),
        "Speed trap": lap["SpeedST"],
        "Tire age (laps)": lap["TireLife"],
    })


def driver_features(tel, corners):
    rows = []
    for driver in tel["Driver"].unique():
        t = tel[tel["Driver"] == driver]
        corner_speeds = [min_speed_near(t, frac) for frac in corners["Frac"]]
        rows.append([driver, t["Team"].iloc[0], t["LapTime_s"].iloc[0], t["Speed"].max(), np.mean(corner_speeds)])
    return pd.DataFrame(rows, columns=["Driver", "Team", "LapTime_s", "TopSpeed", "CornerSpeed"])
