# covid_dashboard_disease_vaccine.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="COVID‑19 Dashboard (disease.sh)", layout="wide")
st.title("🌍 COVID‑19 Dashboard with Vaccinations (disease.sh, 2020‑2023)")

@st.cache_data(ttl=3600)
def load_covid_data(country: str = None):
    """Load historical COVID-19 cases/deaths/recovered"""
    if country is None or country.lower() == "global":
        url = "https://disease.sh/v3/covid-19/historical/all?lastdays=all"
        resp = requests.get(url)
        resp.raise_for_status()
        js = resp.json()
        df = pd.DataFrame({
            "date": list(js["cases"].keys()),
            "confirmed": list(js["cases"].values()),
            "deaths": list(js["deaths"].values()),
            "recovered": list(js.get("recovered", {}).values()) if "recovered" in js else None
        })
    else:
        url = f"https://disease.sh/v3/covid-19/historical/{country}?lastdays=all"
        resp = requests.get(url)
        resp.raise_for_status()
        js = resp.json()
        timeline = js.get("timeline", {})
        df = pd.DataFrame({
            "date": list(timeline["cases"].keys()),
            "confirmed": list(timeline["cases"].values()),
            "deaths": list(timeline["deaths"].values()),
            "recovered": list(timeline["recovered"].values()) if "recovered" in timeline else None
        })
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df = df[(df["year"] >= 2020) & (df["year"] <= 2023)]
    return df

@st.cache_data(ttl=3600)
def load_vaccine_data(country: str):
    """Load vaccination data for a specific country"""
    url = f"https://disease.sh/v3/covid-19/vaccine/coverage/countries/{country}?lastdays=all&fullData=true"
    resp = requests.get(url)
    resp.raise_for_status()
    js = resp.json()
    data = js.get("timeline", [])
    if not data:
        return pd.DataFrame(columns=["date","total"])
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df = df[(df["year"] >= 2020) & (df["year"] <= 2023)]
    return df

# --- Load current COVID data by country ---
@st.cache_data(ttl=3600)
def load_country_data():
    url = "https://disease.sh/v3/covid-19/countries"
    data = requests.get(url).json()
    df = pd.DataFrame(data)
    df["lat"] = df["countryInfo"].apply(lambda x: x.get("lat"))
    df["long"] = df["countryInfo"].apply(lambda x: x.get("long"))
    return df[["country", "cases", "deaths", "recovered", "lat", "long"]]

df = load_country_data()

# --- Bubble Map ---
fig = px.scatter_geo(
    df,
    lat="lat",
    lon="long",
    size="cases",  # bubble size = total cases
    color="cases",
    hover_name="country",
    color_continuous_scale="Reds",
    size_max=40,
    title="Total COVID-19 Cases by Country",
    projection="natural earth"
)

fig.update_layout(
    geo=dict(showframe=False, showcoastlines=True, projection_type="equirectangular"),
)

st.plotly_chart(fig, use_container_width=True)

# --- Sidebar Filters ---
country_input = st.sidebar.selectbox("Select Country", ["Global", "USA", "India", "Brazil", "Germany", "France", "UK", "China", "Japan"])
use_country = country_input if country_input != "Global" else None

# --- Load Data ---
df = load_covid_data(country=use_country)

# Year filter
available_years = sorted(df["year"].unique())
selected_year = st.sidebar.selectbox("Select Year", available_years)
filtered = df[df["year"] == selected_year]

# --- Metrics ---
total_confirmed = int(filtered["confirmed"].max())
total_deaths = int(filtered["deaths"].max())
total_recovered = int(filtered["recovered"].max()) if filtered["recovered"].notna().any() else None

col1, col2, col3 = st.columns(3)
col1.metric("Total Confirmed", f"{total_confirmed:,}")
col2.metric("Total Deaths", f"{total_deaths:,}")
col3.metric("Total Recovered", f"{total_recovered:,}" if total_recovered is not None else "N/A")

# --- Cumulative Trend Chart ---
y_cols = ["confirmed","deaths"] + (["recovered"] if total_recovered is not None else [])
fig = px.line(
    filtered,
    x="date",
    y=y_cols,
    labels={"value":"Count","date":"Date","variable":"Metric"},
    title=f"Cumulative COVID-19 Trends: {country_input} ({selected_year})"
)
st.plotly_chart(fig, use_container_width=True)

# --- Vaccine Section ---
if use_country:
    df_vaccine = load_vaccine_data(use_country)
    if not df_vaccine.empty:
        total_vaccines = int(df_vaccine["total"].max())
        st.subheader(f"💉 COVID-19 Vaccinations in {use_country}")
        st.metric("Total Vaccines Administered", f"{total_vaccines:,}")
        fig_vax = px.line(
            df_vaccine,
            x="date",
            y="total",
            labels={"date":"Date","total":"Doses Administered"},
            title=f"Daily Cumulative Vaccinations: {use_country} (2020-2023)"
        )
        st.plotly_chart(fig_vax, use_container_width=True)
    else:
        st.warning(f"No vaccination data available for {use_country}.")
else:
    st.info("Select a specific country to view vaccination data.")
