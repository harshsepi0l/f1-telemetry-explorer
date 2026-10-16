import fastf1
import pandas as pd
import altair as alt
import streamlit as st

st.title("F1 Telemetry Explorer (prototype)")
st.write("Compare two drivers' fastest laps from 2025 Italian GP qualifying.")


# only load the session once
@st.cache_resource
def load_session():
    fastf1.Cache.enable_cache("f1_cache")
    session = fastf1.get_session(2025, "Italian Grand Prix", "Q")
    session.load()
    return session


session = load_session()
drivers = list(session.results["Abbreviation"])

driver1 = st.selectbox("Driver 1", drivers, index=0)
driver2 = st.selectbox("Driver 2", drivers, index=1)

all_tel = []
times = {}
# rename FastF1's tire columns to use "Tire"
laps = session.laps.rename(columns={"TyreLife": "TireLife", "FreshTyre": "FreshTire"})

for d in [driver1, driver2]:
    lap = laps.pick_drivers(d).pick_fastest()
    tel = lap.get_car_data().add_distance()
    tel["Lap %"] = tel["Distance"] / tel["Distance"].max() * 100
    tel["Driver"] = d
    all_tel.append(tel)
    times[d] = [lap["LapTime"].total_seconds(), lap["Sector1Time"].total_seconds(),
                lap["Sector2Time"].total_seconds(), lap["Sector3Time"].total_seconds()]
    st.write(d, "tires:", lap["Compound"], "(" + str(int(lap["TireLife"])) + " laps old)")

df = pd.concat(all_tel)

st.subheader("Speed around the lap")
chart = alt.Chart(df).mark_line().encode(
    x="Lap %",
    y="Speed",
    color="Driver",
    tooltip=["Driver", "Lap %", "Speed", "Throttle", "nGear"],
).interactive()
st.altair_chart(chart)

st.subheader("Lap and sector times (s)")
st.dataframe(pd.DataFrame(times, index=["Lap", "Sector 1", "Sector 2", "Sector 3"]))
