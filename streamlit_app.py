import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="World GDP Dashboard", page_icon="🌍", layout="wide")
st.title("🌍 World GDP Dashboard")
st.caption("Explore GDP data by country, indicator, and year.")

DATA_FILE = Path("/content/world_gdp_data.csv")

@st.cache_data
def get_gdp_data(file_path):
    df = pd.read_csv(file_path, encoding="latin1")
    df.columns = df.columns.astype(str).str.strip().str.lower()

    required = ["country_name", "indicator_name"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Found: {df.columns.tolist()}")

    year_columns = [c for c in df.columns if c.isdigit() and 1980 <= int(c) <= 2024]
    if not year_columns:
        raise ValueError("No year columns from 1980 to 2024 were found.")

    result = df.melt(
        id_vars=["country_name", "indicator_name"],
        value_vars=year_columns,
        var_name="Year",
        value_name="GDP"
    )
    result["country_name"] = result["country_name"].astype(str).str.strip()
    result["indicator_name"] = result["indicator_name"].astype(str).str.strip()
    result["Year"] = pd.to_numeric(result["Year"], errors="coerce")
    result["GDP"] = pd.to_numeric(result["GDP"], errors="coerce")
    result = result.dropna(subset=["Year", "GDP"])
    result = result[result["country_name"] != ""]
    result["Year"] = result["Year"].astype(int)
    return result

if not DATA_FILE.exists():
    st.error(f"CSV file not found: {DATA_FILE}. Upload world_gdp_data.csv to /content.")
    st.stop()

try:
    gdp_df = get_gdp_data(str(DATA_FILE))
except Exception as error:
    st.error(f"Unable to load GDP data: {error}")
    st.stop()

if gdp_df.empty:
    st.warning("No numeric GDP values were found in the CSV.")
    st.stop()

st.sidebar.header("🔎 Dashboard Filters")
indicators = sorted(gdp_df["indicator_name"].dropna().unique().tolist())
selected_indicator = st.sidebar.selectbox("Select indicator", indicators)
indicator_df = gdp_df[gdp_df["indicator_name"] == selected_indicator]

countries = sorted(indicator_df["country_name"].dropna().unique().tolist())
selected_countries = st.sidebar.multiselect(
    "Select countries",
    options=countries,
    default=countries[:min(5, len(countries))]
)

min_year, max_year = int(indicator_df["Year"].min()), int(indicator_df["Year"].max())
if min_year == max_year:
    year_range = (min_year, max_year)
    st.sidebar.write(f"Year: {min_year}")
else:
    year_range = st.sidebar.slider(
        "Select year range", min_value=min_year, max_value=max_year,
        value=(min_year, max_year), step=1
    )

filtered = indicator_df[indicator_df["Year"].between(year_range[0], year_range[1])]
filtered = filtered[filtered["country_name"].isin(selected_countries)] if selected_countries else filtered.iloc[0:0]

latest_year = year_range[1]
latest = filtered[filtered["Year"] == latest_year]
c1, c2, c3 = st.columns(3)
c1.metric("Countries selected", f'{filtered["country_name"].nunique():,}')
c2.metric(f"Total value in {latest_year}", f'{latest["GDP"].sum():,.2f}' if not latest.empty else "N/A")
c3.metric(f"Average value in {latest_year}", f'{latest["GDP"].mean():,.2f}' if not latest.empty else "N/A")

st.divider()
st.subheader("📈 GDP Trend Over Time")
if filtered.empty:
    st.info("Select at least one country from the sidebar to view charts.")
else:
    trend = px.line(
        filtered.sort_values("Year"), x="Year", y="GDP", color="country_name",
        markers=True, title="GDP values by country and year",
        labels={"GDP": "GDP value", "country_name": "Country"}
    )
    st.plotly_chart(trend, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader(f"🏆 Top Countries in {latest_year}")
        if not latest.empty:
            ranking = latest.groupby("country_name", as_index=False)["GDP"].sum()
            ranking = ranking.sort_values("GDP", ascending=False).head(10).sort_values("GDP")
            bar = px.bar(ranking, x="GDP", y="country_name", orientation="h",
                         labels={"GDP": "GDP value", "country_name": "Country"})
            st.plotly_chart(bar, use_container_width=True)
        else:
            st.info("No values available for the selected year.")

    with right:
        st.subheader("🥧 GDP Distribution")
        if not latest.empty:
            pie_data = latest.groupby("country_name", as_index=False)["GDP"].sum()
            pie_data = pie_data.sort_values("GDP", ascending=False).head(8)
            if (pie_data["GDP"] >= 0).all() and pie_data["GDP"].sum() > 0:
                pie = px.pie(pie_data, names="country_name", values="GDP",
                             title=f"Share among top 8 selected countries ({latest_year})")
                st.plotly_chart(pie, use_container_width=True)
            else:
                st.info("Pie chart needs positive GDP values.")

st.subheader("📋 GDP Data Table")
st.dataframe(filtered.sort_values(["Year", "country_name"]), use_container_width=True, hide_index=True)
st.download_button(
    "⬇️ Download filtered data (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_gdp_data.csv",
    mime="text/csv"
)
st.caption("Charts display the numeric values supplied in your CSV. Verify indicator definitions and units before interpreting totals.")
