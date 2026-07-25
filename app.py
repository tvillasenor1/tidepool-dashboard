"""
San Diego Tidepool Observations Dashboard
Run with: streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

import inat_api
from species_config import (
    ALL_SPECIES_NAMES, CURATED_PROJECTS, SAN_DIEGO_COASTAL_BBOX,
    TIDEPOOL_SITES, TIDEPOOL_SPECIES,
)

st.set_page_config(page_title="SD Tidepool Observations", layout="wide")
st.title("🌊 San Diego Tidepool Species Dashboard")
st.caption("Live data from iNaturalist · updates on every filter change")

# ---------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")

    data_source = st.radio(
        "Data source",
        ["Curated species list (broadest coverage)"] + [f"Project: {name}" for name in CURATED_PROJECTS],
        help=(
            "The curated species list combines a fixed species set with a "
            "geo filter. Project mode instead restricts to observations "
            "tagged into a specific community-curated iNaturalist project, "
            "which is narrower but human-verified."
        ),
    )
    selected_project_id = None
    if data_source.startswith("Project:"):
        project_name = data_source.replace("Project: ", "")
        try:
            selected_project_id = inat_api.resolve_project_id(CURATED_PROJECTS[project_name])
            if selected_project_id is None:
                st.error(f"Could not resolve project slug '{CURATED_PROJECTS[project_name]}'. Check it in species_config.py.")
        except inat_api.INatAPIError as e:
            st.error(str(e))

    site_choice = st.selectbox("Site", ["All San Diego coastal sites"] + list(TIDEPOOL_SITES.keys()))

    group_choice = st.multiselect(
        "Species group", list(TIDEPOOL_SPECIES.keys()), default=list(TIDEPOOL_SPECIES.keys())
    )

    date_range = st.date_input(
        "Date range",
        value=(pd.Timestamp.today() - pd.Timedelta(days=365), pd.Timestamp.today()),
    )

    quality = st.radio(
        "Data quality", ["Research grade only", "Research + Needs ID"], index=1
    )
    quality_grade = "research" if quality.startswith("Research grade") else "research,needs_id"

# Resolve which species names are in scope based on group selection
selected_names = tuple(
    name for group, names in TIDEPOOL_SPECIES.items() if group in group_choice for name in names
) or tuple(ALL_SPECIES_NAMES)

# Resolve scientific names -> taxon IDs (cached 24h)
name_to_id = inat_api.resolve_taxon_ids(selected_names)
taxon_ids = tuple(tid for tid in name_to_id.values() if tid is not None)

# Resolve geo scope
if site_choice == "All San Diego coastal sites":
    geo_kwargs = dict(**SAN_DIEGO_COASTAL_BBOX)
    map_center = {"lat": 32.8, "lng": -117.25, "zoom": 10}
else:
    site = TIDEPOOL_SITES[site_choice]
    geo_kwargs = dict(lat=site["lat"], lng=site["lng"], radius_km=site["radius_km"])
    map_center = {"lat": site["lat"], "lng": site["lng"], "zoom": 13}

d1 = str(date_range[0]) if len(date_range) > 0 else None
d2 = str(date_range[1]) if len(date_range) > 1 else None

if not taxon_ids:
    st.warning("No species matched the current filters — showing nothing. Adjust filters in the sidebar.")
    st.stop()

# ---------------------------------------------------------------------
# Fetch data (each call is cached ~10 min; cache key includes all args)
# ---------------------------------------------------------------------
try:
    with st.spinner("Fetching observations from iNaturalist..."):
        obs_data = inat_api.get_observations(
            taxon_ids=None if selected_project_id else taxon_ids,
            project_id=selected_project_id,
            d1=d1, d2=d2, quality_grade=quality_grade,
            **{k: v for k, v in geo_kwargs.items() if k in
               ("place_id", "lat", "lng", "radius_km", "swlat", "swlng", "nelat", "nelng")},
        )
        species_data = inat_api.get_species_counts(
            taxon_ids=None if selected_project_id else taxon_ids,
            project_id=selected_project_id,
            d1=d1, d2=d2, quality_grade=quality_grade,
            **{k: v for k, v in geo_kwargs.items() if k in ("swlat", "swlng", "nelat", "nelng")},
        )
        hist_data = inat_api.get_histogram(
            interval="month", taxon_ids=None if selected_project_id else taxon_ids,
            project_id=selected_project_id,
            d1=d1, d2=d2, quality_grade=quality_grade,
            **{k: v for k, v in geo_kwargs.items() if k in ("swlat", "swlng", "nelat", "nelng")},
        )
except inat_api.INatAPIError as e:
    st.error(f"Couldn't load data from iNaturalist: {e}")
    st.info("This is usually transient (rate limit or network blip). Try again in a moment, or narrow your filters.")
    st.stop()

total_results = obs_data.get("total_results", 0)
st.metric("Matching observations", f"{total_results:,}")

# ---------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------
st.subheader("Observation Map")
records = obs_data.get("results", [])
map_rows = [
    {
        "lat": r["geojson"]["coordinates"][1],
        "lon": r["geojson"]["coordinates"][0],
        "species": r.get("taxon", {}).get("preferred_common_name") or r.get("taxon", {}).get("name", "Unknown"),
        "observed_on": r.get("observed_on"),
        "observer": r.get("user", {}).get("login"),
    }
    for r in records
    if r.get("geojson")
]
map_df = pd.DataFrame(map_rows)

if not map_df.empty:
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_radius=40,
        get_fill_color=[0, 128, 200, 160],
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=map_center["lat"], longitude=map_center["lng"], zoom=map_center["zoom"])
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view_state,
        tooltip={"text": "{species}\nObserved: {observed_on}\nBy: {observer}"},
    ))
else:
    st.info("No georeferenced observations match these filters yet.")

# ---------------------------------------------------------------------
# Species distribution chart
# ---------------------------------------------------------------------
st.subheader("Species Distribution")
sp_rows = [
    {
        "species": s.get("taxon", {}).get("preferred_common_name") or s.get("taxon", {}).get("name"),
        "count": s.get("count", 0),
    }
    for s in species_data.get("results", [])
]
sp_df = pd.DataFrame(sp_rows).sort_values("count", ascending=False)
if not sp_df.empty:
    fig = px.bar(sp_df, x="species", y="count", title="Observations per species (current filters)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No species-count data for the current filters.")

# ---------------------------------------------------------------------
# Time-series (volume over time)
# ---------------------------------------------------------------------
st.subheader("Observation Volume Over Time")
month_counts = hist_data.get("results", {}).get("month", {})
ts_df = pd.DataFrame(
    [{"month": pd.to_datetime(k), "count": v} for k, v in month_counts.items()]
).sort_values("month")
if not ts_df.empty:
    fig2 = px.line(ts_df, x="month", y="count", markers=True, title="Monthly observation counts")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Not enough data to build a time series for the current filters.")

# ---------------------------------------------------------------------
# Seasonality for a chosen key species
# ---------------------------------------------------------------------
st.subheader("Seasonality of a Key Species")
key_species = st.selectbox("Pick a species", list(name_to_id.keys()))
key_id = name_to_id.get(key_species)
if key_id:
    try:
        with st.spinner("Fetching seasonal pattern..."):
            seasonal = inat_api.get_histogram(
                interval="month_of_year", taxon_ids=(key_id,),
                project_id=selected_project_id, quality_grade=quality_grade,
                **{k: v for k, v in geo_kwargs.items() if k in ("swlat", "swlng", "nelat", "nelng")},
            )
    except inat_api.INatAPIError as e:
        st.error(f"Couldn't load seasonal data: {e}")
        st.stop()
    moy = seasonal.get("results", {}).get("month_of_year", {})
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    moy_df = pd.DataFrame(
        [{"month": month_names[int(m) - 1], "count": c} for m, c in sorted(moy.items(), key=lambda x: int(x[0]))]
    )
    if not moy_df.empty:
        fig3 = px.bar(moy_df, x="month", y="count", title=f"{key_species}: observations by month of year")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No seasonal data available for this species under current filters.")
