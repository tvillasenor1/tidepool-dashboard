# San Diego Tidepool Observations Dashboard — Operational Guide

A live, API-driven dashboard tracking iNaturalist observations of aquatic species
in San Diego's rocky intertidal zones, with an interactive map and charts for
species distribution, observation volume over time, and seasonality.

**Stack:** Python + Streamlit + iNaturalist API v1 + Plotly + pydeck
**Hosting:** Streamlit Community Cloud (free, zero server management)
**Refresh model:** real-time-ish — every filter change triggers a fresh API
call, with a short cache (10 min) so repeated identical queries don't re-hit
the API needlessly.

---

## 1. Why this stack

| Decision | Reasoning |
|---|---|
| **Streamlit** over Flask/Django/React | You get a working interactive dashboard (widgets, charts, map) in one Python file, with far less boilerplate than a separate frontend/backend split. Fits "fastest to build" priority. |
| **Streamlit Community Cloud** for hosting | Free tier, deploys directly from a GitHub repo, no server/infra to manage, HTTPS included. This is the natural home for a Streamlit app; if you outgrow it later, the same app runs unmodified on Render, Fly.io, or a VM. |
| **Pre-aggregated iNaturalist endpoints** (`species_counts`, `histogram`) instead of pulling raw observations and aggregating yourself | Faster, far fewer API calls, and matches what iNaturalist's own site shows — you're not reinventing aggregation logic that already exists server-side. |
| **`st.cache_data` with a 10-minute TTL** | "Real-time-ish" doesn't mean hitting the API on every keystroke. Caching by function arguments means identical filter combinations are instant, while a genuinely new filter combination fetches fresh data. This also keeps you comfortably inside iNaturalist's ~1 req/sec, ~10k req/day guidance. |
| **Curated taxon list resolved to IDs at runtime** (not hardcoded IDs) | Taxon IDs are stable but easy to get wrong from memory. Resolving scientific names via `/v1/taxa` once (cached 24h) means the list is self-correcting and auditable — you can see exactly what taxon each name resolved to. |
| **pydeck for the map, Plotly for charts** | Both are first-class Streamlit citizens (`st.pydeck_chart`, `st.plotly_chart`) with no extra glue code, and both handle the data volumes you'll see here easily. |

### Why the uploaded PDF wasn't used as the API reference

The PDF you provided documents iNaturalist's **old, deprecated widget-era API**
(JSON/ATOM/DwC/widget formats, no aggregation endpoints). The current API is
**v1**, at `https://api.inaturalist.org/v1`, documented interactively at
`https://api.inaturalist.org/v1/docs/`. This guide and the starter code use v1
throughout, since it's the only one with the `species_counts` and `histogram`
endpoints your charts depend on.

---

## 2. Architecture at a glance

```
┌─────────────────┐      ┌──────────────────┐      ┌────────────────────┐
│  iNaturalist     │◄────►│  inat_api.py      │◄────►│  app.py (Streamlit) │
│  API v1 (public) │ HTTP │  - throttling      │      │  - sidebar filters  │
│                  │      │  - caching         │      │  - map (pydeck)     │
└─────────────────┘      │  - taxon resolution│      │  - charts (Plotly)  │
                          └──────────────────┘      └────────────────────┘
                                                              │
                                                              ▼
                                                     Streamlit Community
                                                     Cloud (public URL)
```

No database is required for the "real-time-ish" model you chose — every page
load / filter change fetches live data through the cached API client. (If you
later want historical trend data that outlives iNaturalist's own retention or
want to reduce API load further, see **Section 6: Optional upgrade path**.)

---

## 3. Project files

You already have a working starter project. Layout:

```
tidepool-dashboard/
├── app.py               # Streamlit UI: filters, map, charts
├── inat_api.py           # iNaturalist v1 API client (throttled + cached)
├── species_config.py     # Curated site list + curated species list
├── requirements.txt      # Python dependencies
└── GUIDE.md               # This document
```

### `species_config.py` — what's curated and why
- **`TIDEPOOL_SITES`** — six known SD rocky intertidal access points
  (Cabrillo, Sunset Cliffs, Bird Rock, La Jolla Cove, Ocean Beach, Cardiff
  Reef), each with a lat/lng and a search radius. Used both for the map's
  default view and as an optional per-site filter.
- **`TIDEPOOL_SPECIES`** — ~17 species across five informal groups (anemones,
  echinoderms, mollusks, arthropods, fish) genuinely found in SD tidepools.
  This keeps the dashboard from being diluted by open-ocean or offshore
  observations that happen to fall inside a bounding box.
- **Important:** iNaturalist's `iconic_taxa[]` filter is a *fixed enum*
  (Plantae, Animalia, Mollusca, Actinopterygii, Mammalia, Aves, Reptilia,
  Amphibia, Insecta, Arachnida, Fungi, Protozoa, Chromista, unknown). It does
  **not** have separate categories for crabs, anemones, or sea stars — those
  all fall under generic "Animalia." That's why the curated list uses
  specific `taxon_id`s rather than relying on `iconic_taxa[]` alone.

### `inat_api.py` — the API layer
Four functions, each a thin, cached, throttled wrapper around one v1 endpoint:

| Function | Endpoint | Purpose |
|---|---|---|
| `resolve_taxon_ids()` | `GET /v1/taxa` | Scientific name → taxon ID, cached 24h |
| `get_observations()` | `GET /v1/observations` | Raw georeferenced records → map |
| `get_species_counts()` | `GET /v1/observations/species_counts` | Pre-aggregated per-species totals → distribution chart |
| `get_histogram()` | `GET /v1/observations/histogram` | Pre-aggregated time-bucketed counts → volume-over-time and seasonality charts |

All requests set a descriptive `User-Agent` (edit the placeholder email in
`inat_api.py` to your own contact — this is good API citizenship, not a
requirement, but iNaturalist's team appreciates being able to reach you if
something's off).

### `app.py` — the dashboard
Sidebar controls: site, species group(s), date range, data-quality grade
(`research` vs `research + needs_id`). Main area: a metric (`total matching
observations`), the map, a species-distribution bar chart, a monthly
volume-over-time line chart, and a per-species seasonality chart
(`month_of_year` histogram interval) with a species picker.

---

## 4. Run it locally

```bash
cd tidepool-dashboard
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

This opens the dashboard at `http://localhost:8501`. Try changing filters in
the sidebar — you should see the map, charts, and metric update within a
couple seconds (first load is slower since taxon-ID resolution has to run;
it's cached after that).

**If a species shows 0 observations everywhere:** open `inat_api.py`, call
`resolve_taxon_ids()` for just that name in a Python shell, and confirm it
returns a taxon ID (occasionally a name in the curated list may be a synonym
iNaturalist doesn't recognize as the "active" name — check
`https://www.inaturalist.org/taxa/search?q=<name>` and update
`species_config.py` with whatever the currently accepted name is).

---

## 5. Deploy it — accessible to your research partner (not the public)

**Recommendation: Streamlit Community Cloud, deployed as a private app.**
Free, no server to manage, and it has exactly the access control you need
for sharing with one research partner (or a small known group) without
exposing the dashboard publicly.

### 5.1 Deploy as a private app

1. Push this project to a **private** GitHub repository (not public).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. Click **New app** → select your private repo, branch `main`, main file
   path `app.py`. Community Cloud requests a read-only GitHub deploy key
   to access private repos (GitHub will notify you when this key is
   created — that's expected).
4. Click **Deploy**. You'll get a URL like
   `https://your-app-name.streamlit.app`. Because the source repo is
   private, the deployed app is **private by default** — nobody can view
   it until you explicitly grant access.

### 5.2 Give your research partner access

1. Open your deployed app while signed in to Community Cloud.
2. Click **Share** in the upper-right corner.
3. Enter your partner's email address under viewers and send the invite.
4. They receive an emailed link. If their email is tied to a Google
   account they can sign in with Google OAuth; otherwise they get a
   single-use emailed sign-in link.
5. They now see the live dashboard at your app's URL — no GitHub account
   or password needed on their end. You can add/remove viewers at any time
   from the same **Share** panel.

Every push to `main` auto-redeploys, so updates reach your partner
immediately with no re-invite needed.

### 5.3 Other hosting options, if your needs change later

| Option | Best for | Tradeoff |
|---|---|---|
| **Streamlit Community Cloud (private)** ← recommended above | Small, known group (you + a partner, maybe a lab) | Free tier has modest CPU/memory limits; fine for this app's traffic |
| **Streamlit Community Cloud (public)** | Sharing with the wider community/public later | Anyone with the link can view — no access control |
| **Hugging Face Spaces** | Alternative free host, also supports Streamlit | Private Spaces require a paid HF plan; public is free |
| **Render / Railway / Fly.io** | Full control (custom domain, no Streamlit-specific limits, room to add your own login) | You manage more config; free tiers often sleep when idle (slow first load after inactivity) |
| **Self-hosted (lab server / VPS)** | Full control, data never leaves your institution | You own uptime, security patches, HTTPS setup |
| **ngrok / Tailscale tunnel to your laptop** | Quick one-off demo | Only live while your machine + tunnel are running — not a real deployment |

**Rate-limit note if you later open this up more broadly:** the whole app
shares one iNaturalist rate-limit budget. The 10-minute cache means
repeated identical filter combinations only cost one real API call, but a
wide-open date picker with many concurrent distinct filter combinations
across many users could add up. If that becomes a concern, see the optional
upgrade path (Section 7) for a scheduled local-cache approach.

---

## 6. Using existing iNaturalist Projects

Two relevant projects exist:

- **`san-diego-tide-pool-biodiversity`** ("San Diego Tide Pool Biodiversity") —
  a real, confirmed project comparing biodiversity at Cabrillo (monitored)
  vs. Bird Rock (unmonitored) tidepools. Narrower in scope (two sites) than
  the geo+taxon curation, but human-curated.
- **"San Diego Shell Club Marine Survey"** — likely exists (the San Diego
  Shell Club is a real, active organization) but its exact project slug
  wasn't confirmed during research. Mollusk-only by nature of the club, so
  it wouldn't cover crabs, anemones, sea stars, or fish even if added.

**Neither project alone matches your full target species list or all six
sites**, so they're wired in as an *alternate data source you can toggle to*,
not a replacement for the default curated list:

- `species_config.py` has a `CURATED_PROJECTS` dict mapping a display name
  to a project slug.
- `inat_api.resolve_project_id()` looks up the slug against `/v1/projects/:id`
  at runtime (cached 24h) — same self-correcting pattern as taxon
  resolution. If a slug is wrong or renamed, you get a visible error in the
  app instead of silently-wrong data.
- The sidebar's **Data source** control lets you switch between "Curated
  species list" and any project in `CURATED_PROJECTS`. In project mode, all
  three chart types (map, species distribution, volume over time) restrict
  to `project_id=<resolved id>` instead of your taxon list — useful for
  cross-checking whether the curated-list numbers roughly agree with a
  human-vetted project's numbers.

**To add the Shell Club survey (or any other project):**
1. Open the project on iNaturalist and copy the slug from the URL, e.g.
   `inaturalist.org/projects/<this-part>`.
2. Add a line to `CURATED_PROJECTS` in `species_config.py`.
3. Restart the app — no other code changes needed.

---

## 7. Optional upgrade path (not needed to launch, good to know about)

- **Add a lightweight cache database (SQLite/DuckDB):** if you want faster
  cold-starts, offline resilience, or to serve heavy traffic without
  re-querying iNaturalist per user, add a scheduled job (cron, GitHub
  Actions, or `APScheduler` inside the app) that pulls observations every
  few hours into a local SQLite file, and point the Streamlit app at that
  file instead of the live API. This trades "real-time-ish" for "a few
  hours stale" in exchange for near-zero API load and instant page loads.
- **iNaturalist Projects:** search `https://www.inaturalist.org/projects`
  for an existing "San Diego Tidepools" or similar community project. If
  one exists and is actively curated, you can add `project_id=<id>` to any
  API call for an even cleaner, human-curated dataset instead of (or in
  addition to) the geo+taxon curation used here.
- **Custom checklist expansion:** to broaden the species list, add
  scientific names to `species_config.py` — no other code changes needed,
  since IDs are resolved dynamically.
- **Authentication:** none of this requires an iNaturalist account or API
  key — all endpoints used here are public read-only data.

---

## 8. Key API reference (v1) for anything you want to extend

Base URL: `https://api.inaturalist.org/v1`
Interactive docs: `https://api.inaturalist.org/v1/docs/`
Recommended practices: ~1 request/second, ~10,000 requests/day, use the
highest `per_page` you need (max 200) rather than many small requests.

Useful params across `/observations`, `/observations/species_counts`, and
`/observations/histogram`:

- `taxon_id` — comma-separated list of taxon IDs (includes descendant taxa)
- `place_id` — a curated iNaturalist place ID (find via `/v1/places`)
- `lat`, `lng`, `radius` — circular geo filter (radius in km)
- `swlat`, `swlng`, `nelat`, `nelng` — bounding-box geo filter
- `d1`, `d2` — observed-date range (ISO date or datetime)
- `month`, `year`, `day` — comma-separated integers for calendar filtering
- `quality_grade` — `casual` | `needs_id` | `research`
- `iconic_taxa[]` — fixed enum, see Section 3 note
- `per_page`, `page` — pagination (max 200/page)
- `/observations/histogram` additionally takes `interval` (`day`, `week`,
  `month`, `year`, `month_of_year`, `week_of_year`) and `date_field`
  (`observed` or `created`)

---

## 9. Completeness checklist — what an LLM (or you) needs to build/verify this

**What's fully specified and executable as-is:**
- All four files (`app.py`, `inat_api.py`, `species_config.py`,
  `requirements.txt`) are complete, syntax-checked Python — no placeholders
  or `# TODO: implement this` gaps.
- Every API call has error handling (`INatAPIError`) that surfaces a
  readable message in the UI instead of crashing.
- `get_observations()` paginates (up to 600 records) instead of silently
  truncating at 200.
- No secrets/API keys are required, so there's no credential-management
  step to get wrong.
- Exact deploy steps (Section 5) and local run steps (Section 4) are
  copy-pasteable shell commands.

**What genuinely requires a judgment call or external lookup, and can't be
fully pre-specified:**
- The Shell Club project's exact slug (Section 6) — needs a human (or an
  LLM with live web access) to visit the project page and copy the URL.
- Whether a curated species name has changed its "currently accepted" form
  in iNaturalist's taxonomy (Section 4's troubleshooting note) — this is
  inherently a live-data question, not something a fixed guide can
  guarantee forever.
- `requirements.txt` uses `>=` minimum versions, not pinned exact versions.
  This is intentional (keeps you on current Streamlit/Plotly features) but
  means a future breaking change upstream is possible. If you want fully
  reproducible builds, run `pip freeze > requirements.txt` after your first
  successful install and commit that instead.

**Self-verification checklist (run through this after any build/edit):**
1. `python3 -m py_compile app.py inat_api.py species_config.py` — must
   exit with no errors.
2. `streamlit run app.py` — app loads without a traceback in the terminal.
3. Default filters (all groups, "All San Diego coastal sites", past year)
   show a non-zero **Matching observations** metric.
4. Switching **Site** to a single location narrows the map to that area.
5. Switching **Data source** to the Tide Pool Biodiversity project loads
   without error (confirms `resolve_project_id` is working).
6. Picking a different species in the seasonality dropdown updates that
   chart.
7. Deployed URL (Section 5) loads the same behavior as local.

**Not included, and intentionally out of scope for a v1 build:** automated
tests, CI pipeline, user accounts/saved views, a persistent database, and
alerting/notifications. Section 7 (Optional upgrade path) covers what to add
if you outgrow the live-fetch model.
