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

# --- Curated + broad taxa for San Diego tidepool species -----------------
# Each entry has:
#   name   - scientific name AT ANY RANK (species, genus, family, order...)
#   common - display name used in the UI
#   broad  - True for a higher-rank "catch-all" entry included specifically
#            for comprehensive coverage; False for a hand-picked species.
#
# KEY INSIGHT: iNaturalist's taxon_id filter automatically includes all
# DESCENDANT taxa (confirmed in the official API docs). So pointing at
# order Nudibranchia pulls in every nudibranch species on iNaturalist
# automatically -- far more comprehensive than hand-listing species, and it
# self-updates as new species get added/observed. We mix both styles:
# specific named species (for consistent per-species seasonality charts and
# because broad entries dilute the species-distribution chart) PLUS a broad
# entry per group (for comprehensive "did we miss anything" coverage).
#
# "broad" entries are NOT selected by default in the app (see app.py) --
# they're opt-in via a "Include broad/undiscovered species" toggle, since
# mixing a handful of specific species with one entry that silently expands
# to hundreds of descendant taxa would make per-species charts misleading.
TIDEPOOL_SPECIES = {
    "Anemones": [
        {"name": "Anthopleura elegantissima", "common": "Aggregating anemone", "broad": False},
        {"name": "Anthopleura xanthogrammica", "common": "Giant green anemone", "broad": False},
        {"name": "Anthopleura sola", "common": "Solitary anemone", "broad": False},
        {"name": "Actiniaria", "common": "All sea anemones (broad, order-level)", "broad": True},
    ],
    "Sea stars & urchins (Echinoderms)": [
        {"name": "Pisaster ochraceus", "common": "Ochre sea star", "broad": False},
        {"name": "Leptasterias sp.", "common": "Six-armed sea star", "broad": False},
        {"name": "Strongylocentrotus purpuratus", "common": "Purple sea urchin", "broad": False},
        {"name": "Asteroidea", "common": "All sea stars (broad, class-level)", "broad": True},
        {"name": "Echinoidea", "common": "All sea urchins (broad, class-level)", "broad": True},
    ],
    "Snails, limpets & bivalves (Mollusks)": [
        {"name": "Tegula funebralis", "common": "Black turban snail", "broad": False},
        {"name": "Lottia gigantea", "common": "Owl limpet", "broad": False},
        {"name": "Mytilus californianus", "common": "California mussel", "broad": False},
        {"name": "Kelletia kelletii", "common": "Kellet's whelk", "broad": False},
        {"name": "Gastropoda", "common": "All marine snails/slugs (broad, class-level)", "broad": True},
    ],
    "Nudibranchs": [
        # From southern_california_common_nudibranchs.csv -- scientific
        # names confirmed current as of this writing (e.g. Ceratodoris
        # rosacea, reclassified from Okenia rosacea in 2023/2024).
        {"name": "Flabellinopsis iodinea", "common": "Spanish Shawl", "broad": False},
        {"name": "Hermissenda opalescens", "common": "Opalescent Nudibranch", "broad": False},
        {"name": "Ceratodoris rosacea", "common": "Hopkins' Rose", "broad": False},
        {"name": "Diaulula sandiegensis", "common": "San Diego Dorid", "broad": False},
        {"name": "Felimare californiensis", "common": "California Blue Dorid", "broad": False},
        {"name": "Acanthodoris lutea", "common": "Sandalwood Dorid", "broad": False},
        {"name": "Peltodoris nobilis", "common": "Noble Dorid", "broad": False},
        {"name": "Limacia cockerelli", "common": "Cockerell's Dorid", "broad": False},
        {"name": "Phidiana hiltoni", "common": "Hilton's Aeolid", "broad": False},
        {"name": "Diaphoreolis lagunae", "common": "Laguna Aeolid", "broad": False},
        {"name": "Nudibranchia", "common": "All nudibranchs (broad, order-level)", "broad": True},
    ],
    "Crabs & barnacles (Arthropods)": [
        {"name": "Pachygrapsus crassipes", "common": "Striped shore crab", "broad": False},
        {"name": "Pugettia producta", "common": "Kelp crab", "broad": False},
        {"name": "Tetraclita rubescens", "common": "Volcano barnacle", "broad": False},
        {"name": "Brachyura", "common": "All true crabs (broad, infraorder-level)", "broad": True},
    ],
    "Fish": [
        {"name": "Clinocottus analis", "common": "Woolly sculpin", "broad": False},
        {"name": "Girella nigricans", "common": "Opaleye", "broad": False},
        {"name": "Gibbonsia elegans", "common": "Spotted kelpfish", "broad": False},
        # No broad entry here on purpose: class Actinopterygii (bony fish)
        # is enormous and includes every open-ocean/offshore fish, so a
        # class-level catch-all would dilute "tidepool fish" badly even
        # with the geo filter applied. If you want broader fish coverage,
        # add specific intertidal genera/families instead (e.g. Girellidae,
        # Cottidae) rather than the whole class.
    ],
}

# Flat list of (scientific_name, common_name) used for API lookups and the
# species picker. Excludes broad entries by default -- see
# TIDEPOOL_SPECIES_BROAD below for those.
ALL_SPECIES_NAMES = [
    item["name"] for group in TIDEPOOL_SPECIES.values() for item in group if not item["broad"]
]
NAME_TO_COMMON = {
    item["name"]: item["common"] for group in TIDEPOOL_SPECIES.values() for item in group
}
BROAD_TAXA_NAMES = [
    item["name"] for group in TIDEPOOL_SPECIES.values() for item in group if item["broad"]
]

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
