import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import fastf1

st.set_page_config(page_title="F1 Telemetry Explorer", layout="wide")
st.title("F1 Telemetry Explorer (prototype)")
st.write("Compare two drivers' fastest laps from 2025 Italian GP qualifying.")

# Pirelli sidewall colors
COMPOUND_COLORS = {"SOFT": "#DA291C", "MEDIUM": "#FFD12E", "HARD": "#F0F0EC",
                   "INTERMEDIATE": "#43B02A", "WET": "#0067AD"}
VIEW_W, VIEW_H, PAD = 800, 440, 40                      # track map coordinate space
RACE_HTML = Path(__file__).parent / "race.html"         # animated race view + speed chart (HTML/JS)


@st.cache_resource
def load_session():
    Path("f1_cache").mkdir(exist_ok=True)
    fastf1.Cache.enable_cache("f1_cache")
    session = fastf1.get_session(2025, "Italian Grand Prix", "Q")
    session.load()
    return session


@st.cache_resource
def load_corners(_session):
    # corner numbers + positions from FastF1's circuit info (empty if it can't be fetched)
    try:
        return _session.get_circuit_info().corners
    except Exception:
        return pd.DataFrame(columns=["X", "Y", "Number", "Letter", "Angle", "Distance"])


def get_fastest(session, laps, driver):
    lap = laps.pick_drivers(driver).pick_fastest()

    tel = lap.get_car_data().add_distance()
    tel["Lap %"] = tel["Distance"] / tel["Distance"].max() * 100
    tel["Time_s"] = tel["Time"].dt.total_seconds()

    pos = lap.get_pos_data()
    pos["Time_s"] = pos["Time"].dt.total_seconds()

    # team name + official team color straight from the F1 timing data
    res = session.results.set_index("Abbreviation").loc[driver]
    color = f"#{res['TeamColor']}" if isinstance(res["TeamColor"], str) and res["TeamColor"] else "#888888"
    info = {
        "lap": lap["LapTime"].total_seconds(),
        "s1": lap["Sector1Time"].total_seconds(),
        "s2": lap["Sector2Time"].total_seconds(),
        "s3": lap["Sector3Time"].total_seconds(),
        "compound": str(lap["Compound"]).upper(),
        "tire_age": int(lap["TireLife"]),
        "team": res["TeamName"],
        "color": color,
        "dashed": False,
    }
    return tel, pos, info


def lighten(hex_color, amount):
    # mix a hex color toward white, used to tell teammates apart
    rgb = [int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(c + (255 - c) * amount):02X}" for c in rgb)


def make_projector(pos):
    # Rotate the circuit so its long axis is horizontal, then fit it into the view.
    xy = pos[["X", "Y"]].to_numpy(dtype=float)
    center = xy.mean(axis=0)
    _, _, vt = np.linalg.svd(xy - center, full_matrices=False)
    angle = np.arctan2(vt[0, 1], vt[0, 0])
    rot = np.array([[np.cos(-angle), -np.sin(-angle)], [np.sin(-angle), np.cos(-angle)]])

    r = (xy - center) @ rot.T
    r[:, 1] *= -1  # SVG y points down
    lo, hi = r.min(axis=0), r.max(axis=0)
    scale = min((VIEW_W - 2 * PAD) / (hi[0] - lo[0]), (VIEW_H - 2 * PAD) / (hi[1] - lo[1]))
    offset = np.array([VIEW_W, VIEW_H]) / 2 - (lo + hi) / 2 * scale

    def project(x, y):
        p = np.atleast_2d((np.array([x, y], dtype=float).T - center) @ rot.T)
        p[:, 1] *= -1
        return p * scale + offset

    return project


def rounded(values, nd):
    return [round(float(v), nd) for v in values]


def corner_payload(corners, project, lap_len):
    # each corner: its point on the track, a label spot pushed off to the side, and its % of the lap
    out = []
    for _, c in corners.iterrows():
        on = project(c["X"], c["Y"])[0]
        a = np.radians(c["Angle"])
        off = project(c["X"] + 500 * np.cos(a), c["Y"] + 500 * np.sin(a))[0] - on
        lab = on + off / (np.linalg.norm(off) or 1) * 17
        out.append({"name": f"{int(c['Number'])}{c['Letter'] or ''}", "on": rounded(on, 1),
                    "label": rounded(lab, 1), "pct": round(float(c["Distance"]) / lap_len * 100, 2)})
    return out


def open_runs(flags):
    # (start, end) index pairs of consecutive True values
    edges = np.flatnonzero(np.diff(np.r_[0, flags.astype(int), 0]))
    return list(zip(edges[::2], edges[1::2] - 1))


def drs_zones(tels, tel_ref, pos_ref, project, min_len_s=1.0):
    # DRS channel values 10/12/14 mean the flap is open. In qualifying drivers open it in
    # every zone, so the open stretches on a fastest lap trace out where the zones are.
    best = max(tels, key=lambda t: int((t["DRS"] >= 10).sum()))
    flags = (best["DRS"] >= 10).to_numpy()
    ts, pct = best["Time_s"].to_numpy(), best["Lap %"].to_numpy()
    runs = [(i, j) for i, j in open_runs(flags) if ts[j] - ts[i] >= min_len_s]
    if not runs:
        return []

    # a zone over the start/finish line shows up as one run at the start of the lap and one at the end
    spans = [[(pct[i], pct[j])] for i, j in runs]
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == len(flags) - 1:
        spans = [spans[-1] + spans[0]] + spans[1:-1]

    ref_t, ref_pct = tel_ref["Time_s"].to_numpy(), tel_ref["Lap %"].to_numpy()
    pos_t = pos_ref["Time_s"].to_numpy()
    zones = []
    for n, segs in enumerate(spans, start=1):
        paths = []
        for p0, p1 in segs:
            t0, t1 = np.interp([p0, p1], ref_pct, ref_t)
            tt = np.r_[t0, pos_t[(pos_t > t0) & (pos_t < t1)], t1]
            pts = project(np.interp(tt, pos_t, pos_ref["X"]), np.interp(tt, pos_t, pos_ref["Y"]))
            paths.append([rounded(p, 1) for p in pts])
        zones.append({"n": n, "pct": [[round(float(a), 2), round(float(b), 2)] for a, b in segs], "paths": paths})
    return zones


def driver_payload(code, tel, pos, info, project):
    # everything the browser needs to animate one car, as plain lists
    pts = project(pos["X"].to_numpy(), pos["Y"].to_numpy())
    return {
        "code": code, "team": info["team"], "color": info["color"], "lap": info["lap"],
        "dashed": info["dashed"], "tire": COMPOUND_COLORS.get(info["compound"], "#BBBBBB"),
        "tel": {"t": rounded(tel["Time_s"], 3), "pct": rounded(tel["Lap %"], 3),
                "speed": rounded(tel["Speed"], 1), "throttle": rounded(tel["Throttle"], 1),
                "gear": [int(g) for g in tel["nGear"]], "drs": [int(d >= 10) for d in tel["DRS"]]},
        "pos": {"t": rounded(pos["Time_s"], 3), "x": rounded(pts[:, 0], 2), "y": rounded(pts[:, 1], 2)},
    }


def driver_card(code, info):
    tire = COMPOUND_COLORS.get(info["compound"], "#BBBBBB")
    st.markdown(
        f'<div style="border:3px solid {info["color"]}; border-radius:10px; padding:12px 16px; margin-bottom:8px;">'
        f'<div style="font-size:28px; font-weight:700; color:{info["color"]};">{code}</div>'
        f'<div style="font-size:15px;">{info["team"]}</div>'
        f'<div style="font-size:14px; margin-top:6px;">'
        f'<span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:{tire};'
        f' border:1px solid #555; margin-right:4px;"></span>'
        f'{info["compound"].title()} tires ({info["tire_age"]} laps old)<br>'
        f'lap: <b>{info["lap"]:.3f} s</b></div></div>',
        unsafe_allow_html=True,
    )


session = load_session()
laps = session.laps.rename(columns={"TyreLife": "TireLife", "FreshTyre": "FreshTire"})
drivers = list(session.results["Abbreviation"])

c1, c2 = st.columns(2)
driver1 = c1.selectbox("Driver 1", drivers, index=0)
driver2 = c2.selectbox("Driver 2", drivers, index=1)
if driver1 == driver2:
    st.warning("Pick two different drivers.")
    st.stop()

tel1, pos1, info1 = get_fastest(session, laps, driver1)
tel2, pos2, info2 = get_fastest(session, laps, driver2)

# teammates share a team color, so driver 2 gets a lighter shade and a dashed chart line
if info1["team"] == info2["team"]:
    info2["color"] = lighten(info2["color"], 0.45)
    info2["dashed"] = True

left, right = st.columns(2)
with left:
    driver_card(driver1, info1)
with right:
    driver_card(driver2, info2)

# ---- race view + speed chart, animated in the browser (see race.html) ----
st.subheader("Race around Monza")
st.write("Both fastest laps on the real circuit layout, looping. Green stretches are DRS zones (worked out from "
         "where the drivers opened DRS), corners are numbered, and the dots on the speed chart follow the cars. "
         "Hover the chart for both drivers' telemetry at any point, or click it to jump there.")

project = make_projector(pos1)  # driver 1's racing line draws the track; both cars share it
track_pts = project(pos1["X"].to_numpy(), pos1["Y"].to_numpy())
payload = {
    "view": [VIEW_W, VIEW_H],
    "track": [rounded(p, 1) for p in track_pts],
    "drs": drs_zones([tel1, tel2], tel1, pos1, project),
    "corners": corner_payload(load_corners(session), project, tel1["Distance"].max()),
    "drivers": [driver_payload(driver1, tel1, pos1, info1, project),
                driver_payload(driver2, tel2, pos2, info2, project)],
}
components.html(RACE_HTML.read_text().replace("__DATA__", json.dumps(payload)), height=890)

# ---- times ----
st.subheader("Lap and sector times (s)")
st.dataframe(pd.DataFrame(
    {d: [i["lap"], i["s1"], i["s2"], i["s3"]] for d, i in [(driver1, info1), (driver2, info2)]},
    index=["Lap", "Sector 1", "Sector 2", "Sector 3"],
))