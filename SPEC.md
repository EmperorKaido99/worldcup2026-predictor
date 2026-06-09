# World Cup 2026 Predictor — Project Spec

**Owner:** Kai (EmperorKaido99)
**Status:** Build-ready (pre Claude Code)
**Hard deadline:** Match Outcome Predictor live before first match kickoff (Thursday)
**Type:** Data-science / ML project with a responsive web front end (personal use, public URL)

---

## 1. Goal

A personal web app with three football-prediction tools, built on free historical
data and lightweight ML models, deployed to a public URL and mobile responsive.

Three features, in priority order:

1. **Match Outcome Predictor** — predicts win / draw / loss for upcoming fixtures.
   *Only feature tied to Thursday's kickoff. Ships first.*
2. **Expected Goals (xG) Model** — predicts goal probability per shot; per-team
   dashboards of where strikers and midfielders score from.
3. **Penalty Shootout Predictor** — predicts shot placement (and, data permitting,
   keeper dive direction). Stretch goal.

---

## 2. Triage & build order (read this first)

Three models + three dashboards + live deploy, solo, in two days is not all
shipping well. Sequenced, not parallel:

| Priority | Feature | When | Why |
|----------|---------|------|-----|
| **P0** | Match Outcome Predictor + live deploy | **Before Thursday** | Only feature tied to kickoff; most tractable |
| P1 | xG model + team dashboards | After kickoff | Exploratory; doesn't expire Thursday |
| P2 | Penalty predictor + dashboard | Stretch | Weakest data; build last |

Don't let P1/P2 jeopardise shipping P0 on time.

---

## 3. Tech stack

Two pieces: a Python backend that does all the data science and serves models over
HTTP, and a Next.js front end that consumes those endpoints.

> **Why not Streamlit:** works on a phone but desktop-first and templated — fails the
> "mobile responsive" requirement.
> **Why not C#/.NET:** modeling is doable in ML.NET, but data acquisition
> (`soccerdata`, `statsbombpy`) and football viz (`mplsoccer`) have no .NET equivalent.
> Because the API is decoupled, a **Blazor front end** against the same FastAPI
> endpoints is a viable post-deadline portfolio swap.

| Layer | Choice |
|-------|--------|
| Language (backend) | Python 3.11+ |
| Data | `soccerdata` (ClubElo, FBref, Understat), `statsbombpy` (StatsBomb open data) |
| Wrangling | `pandas`, `numpy` |
| Match model | `scikit-learn` — LogisticRegression + `CalibratedClassifierCV` |
| xG / penalty models | `xgboost` (or `lightgbm`) + `shap` |
| Football viz | `mplsoccer` (rendered server-side to PNG, served by the API) |
| Model persistence | `joblib` (`.joblib` files committed to repo) |
| **API** | **FastAPI** + `uvicorn` |
| **Front end** | **Next.js (App Router) + TypeScript + Tailwind CSS** |
| API hosting | Render or Railway (free tier) |
| Front-end hosting | Vercel (free) |

**No database.** Training is one-off and in-memory; the fitted model file is the
artifact. The API loads the model + a small inputs file. No Supabase, no Postgres.

---

## 4. Data sources & scope

> **Swap point:** if you have a specific fixtures/results API you'd rather use for
> Feature 1, drop it in here. Anything works for the match predictor. But Features
> 2 and 3 *require* shot-level data with positions — StatsBomb open data is the only
> free source that has it. A generic results API cannot power xG or penalties.

- **Feature 1:** ClubElo (Elo) + FBref (results, schedules, goals) via `soccerdata`.
- **Feature 2:** StatsBomb open data via `statsbombpy` — shot x/y, body part, freeze
  frames (defender + GK locations), `statsbomb_xg`. Covers World Cups.
- **Feature 3:** StatsBomb shot end-location (placement) + goalkeeper events.

**Training universe (P0):** men's international matches, ~last 10 years — major
tournaments + qualifiers + friendlies, as available from `soccerdata`.
**Dropdown universe (P0):** the WC2026 participating nations.
**Data refresh:** P0 uses a static snapshot pulled at train time. Re-running
`ingest.py` + `train_match.py` refreshes it. No live refresh in P0.

---

## 5. Feature specs

### 5.1 Match Outcome Predictor (P0)

- **Output semantics:** predicts the **90-minute result** (win / draw / loss).
  Knockout extra-time/penalty progression is out of P0 scope.
- **Features:** Elo rating (each team), Elo difference, recent form (rolling
  pts + goal diff over last N matches), goals scored/conceded rate,
  **neutral-venue flag**, **host-nation bonus** (USA/CAN/MEX only — real home
  advantage at this tournament is limited to hosts).
- **Model:** multinomial LogisticRegression, calibrated (`CalibratedClassifierCV`).
- **Leakage rule:** every feature computed **as of the match date**. No future data.

### 5.2 xG Model (P1)

- **Features:** distance, angle, body part, assist type, defenders in keeper cone
  (from freeze frame), game situation (open play / set piece / penalty).
- **Model:** gradient boosting (goal / no-goal). Handle imbalance
  (`scale_pos_weight` + calibration).
- **Output:** per-player / per-team shot maps + high-xG-zone heatmaps, by position.
- **Front-end note:** pitch maps drawn by `mplsoccer` → FastAPI renders to PNG →
  Next.js displays the image. No pitch geometry rebuilt in React.

### 5.3 Penalty Predictor (P2)

- **Features:** shooter foot, ball placement (3x3 goal grid), keeper tendencies.
- **Model:** gradient boosting — predict placement; keeper dive if data allows.
- **Output:** pick player + keeper → probability grid of where they score.

---

## 6. UI / Dashboard design

**Approach:** mobile-first, Tailwind, App Router. Three routes, one per feature.

### Routes & navigation
- `/` — Match Predictor (P0)
- `/xg` — xG Dashboard (P1)
- `/penalties` — Penalty Predictor (P2)
- **Nav:** bottom tab bar on mobile (thumb-reachable), top nav on desktop (`md:` up).

### Visual direction (default — override if you want)
- **Theme:** dark. Slate/zinc neutrals (`bg-zinc-950`, cards `bg-zinc-900`).
- **Accent:** emerald for primary actions/positive.
- **Semantic probability colors:** win = emerald, draw = amber, loss = rose.
- **Type:** Geist (Next.js default) or Inter. Large numeric readouts for probabilities.
- **Components:** rounded-2xl cards, generous padding, clear focus states.
- **Loading:** every prediction shows a spinner/skeleton (matters — see deploy gotcha).

### Page: Match Predictor `/`
- Header + one-line description.
- Two team selectors (dropdown or searchable combobox), each with flag + name.
- Optional "neutral venue" toggle (default ON; auto-OFF when a host nation plays at home).
- Primary **Predict** button.
- **Result card:** horizontal stacked bar (emerald/amber/rose) showing Win/Draw/Loss %,
  plus the three numbers large. Below: a small "why" readout — Elo diff, recent form
  for each side. One-line confidence note.

### Page: xG Dashboard `/xg` (P1)
- Team selector → position filter (All / Forwards / Midfielders).
- Renders the `mplsoccer` shot-map + heatmap PNG from the API.
- Summary stats strip: shots, goals, total xG, xG/shot.

### Page: Penalty Predictor `/penalties` (P2)
- Player selector + keeper selector.
- Goal-grid (3x3) heatmap of scoring probability.
- Note that this feature is lower-confidence by design (see gaps).

---

## 7. API contract

Base URL injected into the front end via `NEXT_PUBLIC_API_URL`.
**CORS:** FastAPI must allow the Vercel origin (and `localhost:3000` for dev),
or the browser blocks every request.

### `GET /teams`
Populates dropdowns.
```json
{ "teams": [ { "id": "BRA", "name": "Brazil" }, { "id": "ARG", "name": "Argentina" } ] }
```

### `POST /predict-match`  (P0)
Request:
```json
{ "home": "BRA", "away": "ARG", "neutral": true }
```
Response:
```json
{
  "home": "BRA",
  "away": "ARG",
  "neutral": true,
  "probabilities": { "home_win": 0.42, "draw": 0.28, "away_win": 0.30 },
  "context": { "elo_home": 2031, "elo_away": 2019, "form_home": "WWDLW", "form_away": "WDWWL" }
}
```

### `GET /xg/team/{team_id}?position=FW`  (P1)
Returns shot-map/heatmap PNG (or a URL to one) + summary stats.

### `POST /predict-penalty`  (P2)
Request `{ "player_id": "...", "keeper_id": "..." }` → 3x3 probability grid.

### Errors
All errors return `{ "error": "message" }` with an appropriate HTTP status.

---

## 8. Configuration & environment

- **Backend secrets:** none required for `soccerdata`/`statsbombpy` (no API key).
  If you swap in a keyed fixtures API, put the key in `backend/.env` (gitignored).
- **Frontend env:** `NEXT_PUBLIC_API_URL` — `http://localhost:8000` in dev,
  the Render URL in prod (set in Vercel project settings).
- **CORS origins (FastAPI):** `http://localhost:3000` + the Vercel domain.

---

## 9. Honest gaps (agreed, building around them)

1. **Penalty dive direction is not a clean free field anywhere**, StatsBomb included.
   Placement is derivable; dive direction needs inference or hand-labeling.
   Penalty model is lower-confidence — descope to placement-only if needed.
2. **xG class imbalance** — most shots aren't goals. Calibrate or probabilities lie.
3. **Temporal leakage** — every Elo/form/xG feature must be as-of-match-date.
   Gets its own validation pass.
4. **Small international dataset** — ~a few thousand matches in 10 years. Logistic
   regression is the right ceiling; don't over-engineer P0.

---

## 10. Model acceptance criteria (definition of "done" for P0)

Ship P0 only when the match model:
- **Beats the naive baseline** (higher-Elo-team-wins) on a held-out time split.
- Has a **Brier score / log loss** reported and sane (not worse than baseline).
- Is **calibrated** — predicted probabilities roughly match observed frequencies.
- Endpoint returns a valid response for any two WC2026 teams.

---

## 11. Repo structure (monorepo)

```
worldcup-predictor/
├── SPEC.md
├── README.md
├── LICENSE                  # MIT
├── .gitignore               # Node + Python combined
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── api.py               # FastAPI — models, endpoints, CORS
│   ├── models/              # *.joblib (committed)
│   ├── data/
│   │   ├── raw/             # cached pulls (gitignored)
│   │   └── processed/
│   └── src/
│       ├── ingest.py        # soccerdata + statsbombpy pulls
│       ├── features.py      # feature engineering (as-of-date safe)
│       ├── train_match.py   # P0
│       ├── train_xg.py      # P1
│       ├── train_penalty.py # P2
│       └── viz.py           # mplsoccer -> PNG
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── .env.local.example
    ├── app/
    │   ├── layout.tsx       # nav shell (bottom tabs / top nav)
    │   ├── page.tsx         # match predictor
    │   ├── xg/page.tsx
    │   └── penalties/page.tsx
    ├── components/          # TeamSelect, ProbabilityBar, etc.
    └── lib/api.ts           # typed fetch helpers
```

---

## 12. Claude Code sub-agent architecture

Orchestrated by root `CLAUDE.md`. Five sub-agents scoped by pipeline stage:

1. **data-ingestion** — `soccerdata` + `statsbombpy` pulls, caching, raw → `data/raw`.
2. **feature-engineering** — raw events → model tables; owns as-of-date correctness.
3. **modeling** — trains/evaluates all three models, calibration, SHAP, backtesting,
   acceptance criteria.
4. **frontend-api** — FastAPI endpoints + CORS, `mplsoccer` PNG rendering,
   Next.js UI + Tailwind, typed API client.
5. **validation** — leakage checks, Brier/log loss, calibration curves, imbalance sanity.

---

## 13. Deployment & gotchas

- **API (Render/Railway free tier):** spins down when idle; first request after sleep
  cold-starts (~30–50s). The UI must show a loading state so this looks intentional.
- **Frontend (Vercel):** auto-deploys from `main`. Set `NEXT_PUBLIC_API_URL` in project settings.
- **Model files:** commit the `.joblib` (small). Don't commit `data/raw/`.
- **Build:** backend `pip install -r requirements.txt` + `uvicorn api:app`;
  frontend `npm run build`.
- **CORS:** confirm the deployed Vercel domain is in the FastAPI allow-list before testing live.

---

## 14. P0 milestones (to Thursday)

1. Monorepo + Python venv + Node deps installing clean.
2. `ingest.py` pulls Elo + international results, caches locally.
3. `features.py` builds the match feature table (leakage-safe, neutral/host flags).
4. `train_match.py` trains + calibrates + saves `models/match.joblib`.
5. `validation`: meets acceptance criteria (Sec. 10).
6. `api.py`: `GET /teams` + `POST /predict-match`, CORS configured.
7. Next.js `/`: team selects → fetch `/predict-match` → probability bar + context.
8. Deploy: API to Render/Railway, front end to Vercel → public URL.
