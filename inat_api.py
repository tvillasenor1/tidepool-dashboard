"""
Thin client for the iNaturalist v1 REST API (https://api.inaturalist.org/v1).

Design notes:
- Public GET endpoints require no auth/API key.
- iNaturalist's recommended practice is ~1 request/second and roughly
  10k requests/day. We enforce a minimum spacing between calls and
  cache aggressively with Streamlit's cache so repeated filter tweaks
  in the UI don't hammer the API.
- We prefer the pre-aggregated endpoints (species_counts, histogram)
  over pulling raw observations and aggregating client-side, since
  they're faster, cheaper on rate limits, and match what iNaturalist
  itself shows on its "Species" and date-histogram views.
"""

import time
from typing import Iterable, Optional

import requests
import streamlit as st

BASE_URL = "https://api.inaturalist.org/v1"
USER_AGENT = "sd-tidepool-dashboard/1.0 (contact: your-email@example.com)"

_last_call_time = 0.0
_MIN_INTERVAL_SEC = 1.05  # a hair over 1 req/sec to stay safely under the limit


def _throttle():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_INTERVAL_SEC:
        time.sleep(_MIN_INTERVAL_SEC - elapsed)
    _last_call_time = time.time()


class INatAPIError(Exception):
    """Raised when the iNaturalist API can't be reached or returns an error."""


def _get(path: str, params: dict) -> dict:
    _throttle()
    try:
        resp = requests.get(
            f"{BASE_URL}{path}",
            params={k: v for k, v in params.items() if v not in (None, "", [])},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout as e:
        raise INatAPIError(f"iNaturalist API timed out calling {path}.") from e
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        if status == 429:
            raise INatAPIError(
                "Rate limited by iNaturalist (HTTP 429). Wait a bit and retry."
            ) from e
        raise INatAPIError(f"iNaturalist API returned HTTP {status} for {path}.") from e
    except requests.exceptions.RequestException as e:
        raise INatAPIError(f"Network error calling iNaturalist API: {e}") from e


# --------------------------------------------------------------------------
# Taxon resolution: turn scientific names into stable iNaturalist taxon IDs.
# Cached for 24h since taxonomy rarely changes.
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def resolve_taxon_ids(scientific_names: tuple) -> dict:
    """Returns {scientific_name: taxon_id or None if not found}."""
    resolved = {}
    for name in scientific_names:
        data = _get("/taxa", {"q": name, "is_active": "true", "per_page": 3})
        results = data.get("results", [])
        # Prefer an exact scientific-name match among results
        match = next((r for r in results if r.get("name", "").lower() == name.lower()), None)
        resolved[name] = (match or results[0])["id"] if results else None
    return resolved


# --------------------------------------------------------------------------
# Project resolution: turn a project slug into its numeric ID (and confirm
# it actually exists / is spelled right). Cached 24h.
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def resolve_project_id(slug: str) -> Optional[int]:
    data = _get(f"/projects/{slug}", {})
    results = data.get("results", [])
    return results[0]["id"] if results else None


# --------------------------------------------------------------------------
# Observations (raw records) - used for the map view
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 10, show_spinner=False)
def get_observations(
    taxon_ids: Optional[tuple] = None,
    place_id: Optional[int] = None,
    project_id: Optional[int] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    swlat: Optional[float] = None, swlng: Optional[float] = None,
    nelat: Optional[float] = None, nelng: Optional[float] = None,
    d1: Optional[str] = None, d2: Optional[str] = None,
    month: Optional[Iterable[int]] = None,
    quality_grade: str = "research,needs_id",
    per_page: int = 200,
    max_pages: int = 3,
) -> dict:
    """Fetches up to `max_pages` pages (default 600 records) so the map
    isn't silently truncated at 200 on popular filter combinations. Returns
    a dict shaped like a single API response, with `results` concatenated
    across pages and `total_results` from the first page."""
    base_params = {
        "taxon_id": ",".join(map(str, taxon_ids)) if taxon_ids else None,
        "place_id": place_id,
        "project_id": project_id,
        "lat": lat, "lng": lng, "radius": radius_km,
        "swlat": swlat, "swlng": swlng, "nelat": nelat, "nelng": nelng,
        "d1": d1, "d2": d2,
        "month": ",".join(map(str, month)) if month else None,
        "quality_grade": quality_grade,
        "geo": "true",
        "per_page": per_page,
        "order_by": "observed_on",
        "order": "desc",
    }
    all_results = []
    total_results = 0
    for page in range(1, max_pages + 1):
        data = _get("/observations", {**base_params, "page": page})
        total_results = data.get("total_results", 0)
        page_results = data.get("results", [])
        all_results.extend(page_results)
        if len(page_results) < per_page:
            break  # last page reached
    return {"total_results": total_results, "results": all_results}


# --------------------------------------------------------------------------
# Species distribution - pre-aggregated counts per species
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 10, show_spinner=False)
def get_species_counts(
    taxon_ids: Optional[tuple] = None,
    project_id: Optional[int] = None,
    swlat: Optional[float] = None, swlng: Optional[float] = None,
    nelat: Optional[float] = None, nelng: Optional[float] = None,
    d1: Optional[str] = None, d2: Optional[str] = None,
    month: Optional[Iterable[int]] = None,
    quality_grade: str = "research,needs_id",
) -> dict:
    params = {
        "taxon_id": ",".join(map(str, taxon_ids)) if taxon_ids else None,
        "project_id": project_id,
        "swlat": swlat, "swlng": swlng, "nelat": nelat, "nelng": nelng,
        "d1": d1, "d2": d2,
        "month": ",".join(map(str, month)) if month else None,
        "quality_grade": quality_grade,
        "geo": "true",
        "per_page": 200,
    }
    return _get("/observations/species_counts", params)


# --------------------------------------------------------------------------
# Time-series histogram - pre-aggregated counts per time bucket
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 10, show_spinner=False)
def get_histogram(
    interval: str = "month",  # day | week | month | year | month_of_year
    taxon_ids: Optional[tuple] = None,
    project_id: Optional[int] = None,
    swlat: Optional[float] = None, swlng: Optional[float] = None,
    nelat: Optional[float] = None, nelng: Optional[float] = None,
    d1: Optional[str] = None, d2: Optional[str] = None,
    quality_grade: str = "research,needs_id",
) -> dict:
    params = {
        "date_field": "observed",
        "interval": interval,
        "taxon_id": ",".join(map(str, taxon_ids)) if taxon_ids else None,
        "project_id": project_id,
        "swlat": swlat, "swlng": swlng, "nelat": nelat, "nelng": nelng,
        "d1": d1, "d2": d2,
        "quality_grade": quality_grade,
        "geo": "true",
    }
    return _get("/observations/histogram", params)
