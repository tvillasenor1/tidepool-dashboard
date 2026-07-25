"""
Configuration for the San Diego Tidepool Observations Dashboard.

Two curation strategies are supported and can be combined:
  1. GEO CURATION  - a bounding box / set of named sites covering SD's
     rocky intertidal zones.
  2. TAXON CURATION - a hand-picked list of species that are genuinely
     found in local tidepools, so the dashboard isn't diluted by e.g.
     open-ocean fish or offshore observations that happen to fall in
     the bounding box.

Taxon IDs are NOT hardcoded here because they can change / be wrong if
typed from memory. `inat_api.resolve_taxon_ids()` looks them up from
the live /v1/taxa endpoint the first time the app runs and caches the
result, so the list below only needs scientific names.
"""

# --- Known San Diego rocky intertidal / tidepool sites -------------------
# Used for map default view + optional per-site filtering.
# lat/lng are approximate site centers; radius_km is a reasonable search
# radius that captures the accessible tidepool area without pulling in
# unrelated inland observations.
TIDEPOOL_SITES = {
    "Cabrillo National Monument": {"lat": 32.6725, "lng": -117.2410, "radius_km": 1.0},
    "Sunset Cliffs": {"lat": 32.7157, "lng": -117.2544, "radius_km": 1.5},
    "Bird Rock, La Jolla": {"lat": 32.8078, "lng": -117.2735, "radius_km": 1.0},
    "La Jolla Cove / Coast Walk": {"lat": 32.8508, "lng": -117.2713, "radius_km": 1.5},
    "Ocean Beach": {"lat": 32.7495, "lng": -117.2517, "radius_km": 1.0},
    "Cardiff Reef / San Elijo": {"lat": 33.0119, "lng": -117.2810, "radius_km": 1.5},
}

# Overall bounding box covering all sites above, used as the default
# "All San Diego" map extent and as a swlat/swlng/nelat/nelng filter.
SAN_DIEGO_COASTAL_BBOX = {
    "swlat": 32.53,
    "swlng": -117.30,
    "nelat": 33.05,
    "nelng": -117.20,
}

# --- Curated list of common San Diego tidepool species --------------------
# Grouped by informal category for chart legends/filters. Scientific names
# are used for lookup since common names are ambiguous in the API.
TIDEPOOL_SPECIES = {
    "Anemones": [
        "Anthopleura elegantissima",   # Aggregating anemone
        "Anthopleura xanthogrammica",  # Giant green anemone
        "Anthopleura sola",            # Solitary anemone
    ],
    "Sea stars & urchins (Echinoderms)": [
        "Pisaster ochraceus",          # Ochre sea star
        "Leptasterias sp.",            # Six-armed sea star
        "Strongylocentrotus purpuratus",  # Purple sea urchin
    ],
    "Snails & limpets (Mollusks)": [
        "Tegula funebralis",           # Black turban snail
        "Lottia gigantea",             # Owl limpet
        "Aplysia californica",         # California sea hare
        "Mytilus californianus",       # California mussel
        "Kelletia kelletii",           # Kellet's whelk
    ],
    "Crabs & barnacles (Arthropods)": [
        "Pachygrapsus crassipes",      # Striped shore crab
        "Pugettia producta",           # Kelp crab
        "Tetraclita rubescens",        # Volcano barnacle
    ],
    "Fish": [
        "Clinocottus analis",          # Woolly sculpin
        "Girella nigricans",           # Opaleye
        "Gibbonsia elegans",           # Spotted kelpfish
    ],
}

# Flat list used for API lookups
ALL_SPECIES_NAMES = [name for group in TIDEPOOL_SPECIES.values() for name in group]

# --- Optional: community-curated iNaturalist Projects ---------------------
# Projects are a supplementary/cross-check data source, not a replacement
# for the geo+taxon curation above -- no single known project covers the
# full target species list across all sites. Project slugs are resolved to
# IDs dynamically via inat_api.resolve_project_id() (same pattern as taxa),
# so a wrong/renamed slug fails loudly instead of silently hardcoding a bad
# ID. Confirm each slug from the project's URL, e.g.
# inaturalist.org/projects/<slug>.
CURATED_PROJECTS = {
    "San Diego Tide Pool Biodiversity": "san-diego-tide-pool-biodiversity",
    # Mollusk-only club survey -- confirm the exact slug from the project's
    # URL before enabling; search hasn't turned up a confirmed slug yet.
    # "San Diego Shell Club Marine Survey": "<paste-confirmed-slug-here>",
}

# iconic_taxa fallback filter, used only in "explore beyond the curated
# list" mode (geo-only search without a fixed taxon_id list).
# NOTE: iNaturalist's iconic_taxa is a fixed enum - it does NOT include
# "Arthropoda", "Cnidaria", or "Echinodermata" as their own categories
# (crabs, anemones, and sea stars all fall under the generic "Animalia").
# Mollusca and Actinopterygii (fish) ARE valid iconic taxa. For
# crustaceans/cnidarians/echinoderms, filter by taxon_id instead (see
# TIDEPOOL_SPECIES above) rather than relying on iconic_taxa[].
INTERTIDAL_ICONIC_TAXA = ["Mollusca", "Actinopterygii"]
