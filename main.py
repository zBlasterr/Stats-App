import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ Football Stats",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; }
.section-header {
  font-family: 'Bebas Neue', sans-serif; font-size: 22px; color: #f0f6fc;
  border-left: 4px solid #238636; padding-left: 12px;
  margin: 28px 0 12px 0; letter-spacing: 1px;
}
.source-badge-fd {
  display: inline-block; background: #0d2d5e; color: #79c0ff;
  border: 1px solid #1f6feb; border-radius: 20px;
  padding: 3px 12px; font-size: 12px; font-weight: 600; margin-bottom: 10px;
}
.source-badge-af {
  display: inline-block; background: #0d4429; color: #3fb950;
  border: 1px solid #238636; border-radius: 20px;
  padding: 3px 12px; font-size: 12px; font-weight: 600; margin-bottom: 10px;
}
.source-badge-both {
  display: inline-block; background: #2d1b69; color: #d2a8ff;
  border: 1px solid #8957e5; border-radius: 20px;
  padding: 3px 12px; font-size: 12px; font-weight: 600; margin-bottom: 10px;
}
div[data-testid="stMetric"] {
  background: #161b22; border: 1px solid #30363d;
  border-radius: 10px; padding: 16px;
}
div[data-testid="stMetricValue"] { color: #f0f6fc !important; font-size: 26px !important; }
div[data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 12px !important; }
.stSelectbox > div > div { background: #161b22 !important; border-color: #30363d !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────────────────────────────────────
PT = {"paper": "#0d1117", "plot": "#161b22", "font": "#c9d1d9", "grid": "#21262d"}

def sf(fig, height=None):
    kw = dict(paper_bgcolor=PT["paper"], plot_bgcolor=PT["plot"],
              font=dict(color=PT["font"], family="Inter"),
              margin=dict(l=20, r=20, t=40, b=20))
    if height:
        kw["height"] = height
    fig.update_layout(**kw)
    fig.update_xaxes(gridcolor=PT["grid"], zerolinecolor=PT["grid"])
    fig.update_yaxes(gridcolor=PT["grid"], zerolinecolor=PT["grid"])
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# API KEYS
# ─────────────────────────────────────────────────────────────────────────────
def _secret(key: str) -> str:
    try:
        return st.secrets[key]
    except Exception:
        return ""

FD_KEY  = _secret("FOOTBALL_DATA_KEY")   # football-data.org
AF_KEY  = _secret("API_FOOTBALL_KEY")    # api-football.com (opcional)
BZ_KEY  = _secret("BZZOIRO_KEY")         # sports.bzzoiro.com (gratis, sem rate limit)

HAS_FD  = bool(FD_KEY)
HAS_AF  = bool(AF_KEY)
HAS_BZ  = bool(BZ_KEY)
HAS_ANY = HAS_FD or HAS_AF or HAS_BZ

# Throttle para API-Football (max 8 req/min)
import time as _time
if "af_req_times" not in st.session_state:
    st.session_state["af_req_times"] = []

def _af_throttle():
    now = _time.time()
    st.session_state["af_req_times"] = [t for t in st.session_state["af_req_times"] if now - t < 60]
    if len(st.session_state["af_req_times"]) >= 8:
        wait = 60 - (now - st.session_state["af_req_times"][0]) + 0.5
        if wait > 0:
            st.toast(f"API-Football: aguardando {wait:.0f}s (rate limit)...", icon="\u23f3")
            _time.sleep(wait)
    st.session_state["af_req_times"].append(_time.time())

# ─────────────────────────────────────────────────────────────────────────────
# RAW REQUEST HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _fd_get(endpoint: str, params: dict = None) -> dict | None:
    if not FD_KEY:
        return None
    try:
        r = requests.get(
            f"https://api.football-data.org/v4{endpoint}",
            headers={"X-Auth-Token": FD_KEY},
            params=params, timeout=12,
        )
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 403:
            st.error("football-data.org: Chave inválida ou liga não disponível no plano gratuito.")
        elif r.status_code == 429:
            st.warning("football-data.org: Limite de requisições atingido.")
        else:
            st.error(f"football-data.org HTTP {r.status_code}")
        return None
    except Exception as e:
        st.error(f"football-data.org conexão: {e}"); return None


def _af_get(endpoint: str, params: dict = None) -> dict | None:
    if not AF_KEY:
        return None
    _af_throttle()
    try:
        r = requests.get(
            f"https://v3.football.api-sports.io{endpoint}",
            headers={"x-apisports-key": AF_KEY},
            params=params, timeout=12,
        )
        if r.status_code == 200:
            body = r.json()
            if body.get("errors"):
                st.error(f"API-Football: {body['errors']}")
                return None
            return body
        elif r.status_code == 429:
            st.warning("API-Football: Limite de requisições atingido (10 req/min).")
        else:
            st.error(f"API-Football HTTP {r.status_code}")
        return None
    except Exception as e:
        st.error(f"API-Football conexão: {e}"); return None

def _bz_get(endpoint: str, params: dict = None) -> dict | None:
    """Bzzoiro Sports Data — gratuita, sem rate limit, sem cartao."""
    if not BZ_KEY:
        return None
    try:
        r = requests.get(
            f"https://sports.bzzoiro.com{endpoint}",
            headers={"Authorization": f"Token {BZ_KEY}"},
            params=params, timeout=12,
        )
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 401:
            st.error("Bzzoiro: Chave invalida. Verifique BZZOIRO_KEY.")
        elif r.status_code == 404:
            return None  # silently — resource may not exist for this league
        else:
            st.error(f"Bzzoiro HTTP {r.status_code}")
        return None
    except Exception as e:
        st.error(f"Bzzoiro conexao: {e}"); return None

# ─────────────────────────────────────────────────────────────────────────────
# LEAGUE CONFIG  (IDs para cada API)
# ─────────────────────────────────────────────────────────────────────────────
LEAGUES = {
    # Calendário dentro do ano (Jan–Dez) → temporada atual = 2025
    "🇧🇷 Brasileirão Série A": {
        "flag": "🇧🇷",
        "fd_id": 2013, "fd_free": True,
        "af_id": 71,
        "af_season_default": 2025,   # temporada começa em Abril/2025
        "af_season_type": "calendar",
        "bz_id": 9, # Jan–Dez
    },
    # Calendário europeu (Ago–Mai) → temporada atual = 2024 (2024/25)
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": {
        "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "fd_id": 2021, "fd_free": True,
        "af_id": 39,
        "af_season_default": 2024,
        "af_season_type": "european",
        "bz_id": 1,
    },
    "🇪🇸 La Liga": {
        "flag": "🇪🇸",
        "fd_id": 2014, "fd_free": True,
        "af_id": 140,
        "af_season_default": 2024,
        "af_season_type": "european",
        "bz_id": 3,
    },
    "🇩🇪 Bundesliga": {
        "flag": "🇩🇪",
        "fd_id": 2002, "fd_free": True,
        "af_id": 78,
        "af_season_default": 2024,
        "af_season_type": "european",
        "bz_id": 5,
    },
    "🇫🇷 Ligue 1": {
        "flag": "🇫🇷",
        "fd_id": 2015, "fd_free": False,
        "af_id": 61,
        "af_season_default": 2024,
        "af_season_type": "european",
        "bz_id": 6,
    },
    "🇵🇹 Liga Portugal": {
        "flag": "🇵🇹",
        "fd_id": 2017, "fd_free": False,
        "af_id": 94,
        "af_season_default": 2024,
        "af_season_type": "european",
        "bz_id": 2,
    },
    "🇮🇹 Serie A": {
        "flag": "🇮🇹",
        "fd_id": 2019, "fd_free": False,
        "af_id": 135,
        "af_season_default": 2024,
        "af_season_type": "european",
        "bz_id": 4,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA FUNCTIONS — Bzzoiro Sports Data  (sports.bzzoiro.com)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def bz_standings(bz_league_id: int) -> pd.DataFrame:
    data = _bz_get("/api/standings/", {"league": bz_league_id})
    if not data:
        return pd.DataFrame()
    rows = []
    standings = data if isinstance(data, list) else data.get("standings", data.get("results", []))
    for e in standings:
        team = e.get("team", {}) if isinstance(e.get("team"), dict) else {"name": e.get("team_name", ""), "id": e.get("team_id", 0)}
        rows.append({
            "Pos":      e.get("rank", e.get("position", 0)),
            "Time":     team.get("name", e.get("team_name", "")),
            "team_id_bz": team.get("id", e.get("team_id", 0)),
            "PJ":  e.get("played", e.get("games_played", 0)),
            "V":   e.get("won", e.get("wins", 0)),
            "E":   e.get("drawn", e.get("draws", 0)),
            "D":   e.get("lost", e.get("losses", 0)),
            "GP":  e.get("goals_for", e.get("goals_scored", 0)),
            "GC":  e.get("goals_against", e.get("goals_conceded", 0)),
            "SG":  e.get("goal_difference", 0),
            "Pts": e.get("points", 0),
            "Forma": e.get("form", ""),
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def bz_players(bz_league_id: int) -> pd.DataFrame:
    """Fetch player list for a league, then enrich with per-match stats."""
    data = _bz_get("/api/players/", {"league": bz_league_id})
    if not data:
        return pd.DataFrame()
    results = data if isinstance(data, list) else data.get("results", [])
    rows = []
    for p in results:
        team = p.get("team", {}) if isinstance(p.get("team"), dict) else {}
        rows.append({
            "player_id": p.get("id", 0),
            "Jogador":   p.get("name", ""),
            "Posição":   p.get("position", ""),
            "Nac.":      p.get("nationality", ""),
            "Foto":      p.get("photo", ""),
            "Time":      team.get("name", p.get("team_name", "")),
            "Valor (M€)": p.get("market_value_eur", 0),
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def bz_player_stats(bz_league_id: int) -> pd.DataFrame:
    """Aggregate per-match player stats into season totals."""
    data = _bz_get("/api/player-stats/", {"league": bz_league_id, "limit": 500})
    if not data:
        return pd.DataFrame()
    results = data if isinstance(data, list) else data.get("results", [])
    if not results:
        return pd.DataFrame()

    # Aggregate by player
    from collections import defaultdict
    agg = defaultdict(lambda: {
        "Jogador": "", "Time": "", "Posição": "", "Foto": "",
        "Jogos": 0, "Minutos": 0, "Gols": 0, "Assistencias": 0,
        "Chutes": 0, "Chutes_alvo": 0,
        "Passes": 0, "Passes_chave": 0,
        "Desarmes": 0, "Interceptacoes": 0,
        "Amarelos": 0, "Vermelhos": 0,
        "xG_sum": 0.0, "xA_sum": 0.0,
        "Nota_sum": 0.0, "Nota_cnt": 0,
        "Dribles_suc": 0, "Dribles_att": 0,
    })

    for s in results:
        pid = s.get("player") or s.get("player_id") or s.get("id", 0)
        a = agg[pid]
        a["Jogador"]  = s.get("player_name", a["Jogador"])
        a["Time"]     = s.get("team_name", a["Time"])
        a["Posição"]  = s.get("position", a["Posição"])
        a["Foto"]     = s.get("player_photo", a["Foto"])
        a["Jogos"]   += 1
        a["Minutos"] += s.get("minutes_played", 0) or 0
        a["Gols"]    += s.get("goals", 0) or 0
        a["Assistencias"] += s.get("assists", 0) or 0
        a["Chutes"]  += s.get("shots_total", 0) or 0
        a["Chutes_alvo"] += s.get("shots_on_target", 0) or 0
        a["Passes"]  += s.get("passes_total", 0) or 0
        a["Passes_chave"] += s.get("key_passes", 0) or 0
        a["Desarmes"] += s.get("tackles", 0) or 0
        a["Interceptacoes"] += s.get("interceptions", 0) or 0
        a["Amarelos"] += s.get("yellow_cards", 0) or 0
        a["Vermelhos"] += s.get("red_cards", 0) or 0
        a["xG_sum"]  += float(s.get("xg", 0) or 0)
        a["xA_sum"]  += float(s.get("xa", 0) or 0)
        rating = s.get("rating")
        if rating:
            try:
                a["Nota_sum"] += float(rating); a["Nota_cnt"] += 1
            except Exception:
                pass
        a["Dribles_suc"] += s.get("dribbles_success", 0) or 0
        a["Dribles_att"] += s.get("dribbles_attempts", 0) or 0

    rows = []
    for pid, a in agg.items():
        mins = a["Minutos"]
        p90  = mins / 90 if mins >= 45 else None
        gols90    = round(a["Gols"]        / p90, 2) if p90 else 0
        assists90 = round(a["Assistencias"]/ p90, 2) if p90 else 0
        ga90      = round((a["Gols"]+a["Assistencias"]) / p90, 2) if p90 else 0
        shots90   = round(a["Chutes"]      / p90, 2) if p90 else 0
        tack90    = round(a["Desarmes"]    / p90, 2) if p90 else 0
        conv      = round(a["Gols"]/a["Chutes"]*100, 1) if a["Chutes"] > 0 else 0
        drib_r    = round(a["Dribles_suc"]/a["Dribles_att"]*100, 1) if a["Dribles_att"] > 0 else 0
        nota      = round(a["Nota_sum"]/a["Nota_cnt"], 2) if a["Nota_cnt"] > 0 else None

        rows.append({
            "Jogador":          a["Jogador"],
            "Time":             a["Time"],
            "Posição":          a["Posição"],
            "Foto":             a["Foto"],
            "Jogos":            a["Jogos"],
            "Minutos":          mins,
            "Nota":             nota,
            "Gols":             a["Gols"],
            "Assistências":     a["Assistencias"],
            "G+A":              a["Gols"] + a["Assistencias"],
            "xG":               round(a["xG_sum"], 2),
            "xA":               round(a["xA_sum"], 2),
            "xG+xA":            round(a["xG_sum"] + a["xA_sum"], 2),
            "Gols/90":          gols90,
            "Assists/90":       assists90,
            "G+A/90":           ga90,
            "Chutes":           a["Chutes"],
            "Chutes no Alvo":   a["Chutes_alvo"],
            "Chutes/90":        shots90,
            "Conversão (%)":    conv,
            "Passes":           a["Passes"],
            "Passes-Chave":     a["Passes_chave"],
            "Precisão Pass (%)": 0,
            "Dribles Tent.":    a["Dribles_att"],
            "Dribles Suc.":     a["Dribles_suc"],
            "Drible (%)":       drib_r,
            "Desarmes":         a["Desarmes"],
            "Interceptações":   a["Interceptacoes"],
            "Bloqueios":        0,
            "Desarmes/90":      tack90,
            "Amarelos":         a["Amarelos"],
            "Vermelhos":        a["Vermelhos"],
            "Faltas Sofridas":  0,
            "Faltas Cometidas": 0,
            "Pen. Marcados":    0,
            "Pen. Perdidos":    0,
            "Defesas (GK)":     0,
            "Gols Sofridos (GK)": 0,
        })
    df = pd.DataFrame(rows).sort_values("G+A", ascending=False).reset_index(drop=True)
    return df

@st.cache_data(ttl=3600)
def bz_matches(bz_league_id: int, finished: bool = True, limit: int = 30) -> pd.DataFrame:
    status = "finished" if finished else "notstarted"
    data = _bz_get("/api/events/", {"league": bz_league_id, "status": status})
    if not data:
        return pd.DataFrame()
    events = data if isinstance(data, list) else data.get("results", [])
    rows = []
    for m in (events[-limit:] if finished else events[:limit]):
        score = m.get("score", {}) or {}
        gh = score.get("home")
        ga = score.get("away")
        dt = (m.get("event_date") or m.get("date") or "")[:10]
        rows.append({
            "Data":   dt,
            "Casa":   m.get("home_team", ""),
            "Fora":   m.get("away_team", ""),
            "Placar": f"{gh} – {ga}" if gh is not None else "—",
            "GH":     gh or 0,
            "GA":     ga or 0,
            "Rodada": m.get("round", m.get("matchday", "")),
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# SEASON HELPERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)   # cache 24h — seasons don't change often
def af_available_seasons(af_league_id: int) -> list[int]:
    """Fetch all seasons available for a given league from API-Football."""
    data = _af_get("/leagues", {"id": af_league_id})
    if not data:
        return []
    try:
        seasons = data["response"][0]["seasons"]
        return sorted([s["year"] for s in seasons], reverse=True)
    except (IndexError, KeyError):
        return []

def season_label(year: int, season_type: str) -> str:
    """Human-readable season label."""
    if season_type == "european":
        return f"{year}/{str(year+1)[-2:]}"
    return str(year)

# ─────────────────────────────────────────────────────────────────────────────
# DATA FUNCTIONS — football-data.org
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fd_standings(league_fd_id: int) -> pd.DataFrame:
    data = _fd_get(f"/competitions/{league_fd_id}/standings")
    if not data:
        return pd.DataFrame()
    rows = []
    for e in data["standings"][0]["table"]:
        t = e["team"]
        rows.append({
            "Pos": e["position"], "Time": t["name"], "Logo": t.get("crest",""),
            "team_id_fd": t["id"],
            "PJ": e["playedGames"], "V": e["won"], "E": e["draw"], "D": e["lost"],
            "GP": e["goalsFor"],    "GC": e["goalsAgainst"],
            "SG": e["goalsDiff"],   "Pts": e["points"],
            "Forma": e.get("form",""),
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def fd_top_scorers(league_fd_id: int) -> pd.DataFrame:
    data = _fd_get(f"/competitions/{league_fd_id}/scorers", {"limit": 20})
    if not data:
        return pd.DataFrame()
    rows = []
    for s in data.get("scorers", []):
        p = s["player"]; team = s.get("team", {})
        rows.append({
            "Jogador": p["name"], "Time": team.get("name",""),
            "Gols": s.get("goals",0) or 0,
            "Assistências": s.get("assists",0) or 0,
            "Partidas": s.get("playedMatches",0) or 0,
            "Pênaltis": s.get("penalties",0) or 0,
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def fd_matches(league_fd_id: int, status: str = "FINISHED", limit: int = 30) -> pd.DataFrame:
    data = _fd_get(f"/competitions/{league_fd_id}/matches", {"status": status})
    if not data:
        return pd.DataFrame()
    matches = data.get("matches", [])
    matches = matches[-limit:] if status == "FINISHED" else matches[:limit]
    rows = []
    for m in matches:
        ft = m.get("score",{}).get("fullTime",{})
        gh, ga = ft.get("home"), ft.get("away")
        rows.append({
            "Data":    m["utcDate"][:10],
            "Casa":    m["homeTeam"]["name"],
            "Fora":    m["awayTeam"]["name"],
            "Placar":  f"{gh} – {ga}" if gh is not None else "—",
            "GH": gh or 0, "GA": ga or 0,
            "Rodada":  m.get("matchday",""),
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# DATA FUNCTIONS — API-Football
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def af_standings(league_af_id: int, season: int) -> pd.DataFrame:
    data = _af_get("/standings", {"league": league_af_id, "season": season})
    if not data:
        return pd.DataFrame()
    try:
        table = data["response"][0]["league"]["standings"][0]
    except (IndexError, KeyError):
        return pd.DataFrame()
    rows = []
    for e in table:
        t = e["team"]
        rows.append({
            "Pos": e["rank"], "Time": t["name"], "Logo": t.get("logo",""),
            "team_id_af": t["id"],
            "PJ": e["all"]["played"], "V": e["all"]["win"],
            "E": e["all"]["draw"],    "D": e["all"]["lose"],
            "GP": e["all"]["goals"]["for"],
            "GC": e["all"]["goals"]["against"],
            "SG": e["goalsDiff"],     "Pts": e["points"],
            "Forma": e.get("form",""),
        })
    return pd.DataFrame(rows)

def _parse_af_players(response: list) -> pd.DataFrame:
    rows = []
    for item in response:
        p = item.get("player", {}); s = (item.get("statistics") or [{}])[0]
        games    = s.get("games", {})
        goals    = s.get("goals", {})
        shots    = s.get("shots", {})
        passes   = s.get("passes", {})
        dribles  = s.get("dribbles", {})
        tackles  = s.get("tackles", {})
        cards    = s.get("cards", {})
        penalty  = s.get("penalty", {})
        fouls    = s.get("fouls", {})

        minutes  = games.get("minutes") or 0
        apps     = games.get("appearences") or 0
        try:
            rating = round(float(games.get("rating") or 0), 2) or None
        except Exception:
            rating = None

        gols    = goals.get("total") or 0
        assists = goals.get("assists") or 0
        saves   = goals.get("saves") or 0
        conc    = goals.get("conceded") or 0

        shots_t = shots.get("total") or 0
        shots_o = shots.get("on") or 0
        pass_t  = passes.get("total") or 0
        pass_k  = passes.get("key") or 0
        pass_a  = passes.get("accuracy") or 0
        dri_a   = dribles.get("attempts") or 0
        dri_s   = dribles.get("success") or 0
        tack    = tackles.get("total") or 0
        ints    = tackles.get("interceptions") or 0
        blk     = tackles.get("blocks") or 0
        yellow  = cards.get("yellow") or 0
        red     = cards.get("red") or 0
        pen_s   = penalty.get("scored") or 0
        pen_m   = penalty.get("missed") or 0
        f_drawn = fouls.get("drawn") or 0
        f_com   = fouls.get("committed") or 0

        p90       = minutes / 90 if minutes > 0 else None
        gols90    = round(gols    / p90, 2) if p90 else 0
        assists90 = round(assists / p90, 2) if p90 else 0
        ga90      = round((gols + assists) / p90, 2) if p90 else 0
        shots90   = round(shots_t / p90, 2) if p90 else 0
        tack90    = round(tack    / p90, 2) if p90 else 0
        conv      = round(gols / shots_t * 100, 1) if shots_t > 0 else 0
        drib_r    = round(dri_s / dri_a * 100, 1) if dri_a > 0 else 0

        rows.append({
            "Jogador": p.get("name",""), "Idade": p.get("age",""),
            "Nac.": p.get("nationality",""), "Foto": p.get("photo",""),
            "Time": s.get("team",{}).get("name",""),
            "Posição": games.get("position",""),
            "Jogos": apps, "Minutos": minutes, "Nota": rating,
            "Gols": gols, "Assistências": assists, "G+A": gols+assists,
            "Gols/90": gols90, "Assists/90": assists90, "G+A/90": ga90,
            "Chutes": shots_t, "Chutes no Alvo": shots_o,
            "Chutes/90": shots90, "Conversão (%)": conv,
            "Passes": pass_t, "Passes-Chave": pass_k,
            "Precisão Pass (%)": pass_a,
            "Dribles Tent.": dri_a, "Dribles Suc.": dri_s, "Drible (%)": drib_r,
            "Desarmes": tack, "Interceptações": ints, "Bloqueios": blk,
            "Desarmes/90": tack90,
            "Amarelos": yellow, "Vermelhos": red,
            "Faltas Sofridas": f_drawn, "Faltas Cometidas": f_com,
            "Pen. Marcados": pen_s, "Pen. Perdidos": pen_m,
            "Defesas (GK)": saves, "Gols Sofridos (GK)": conc,
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def af_top_scorers(league_af_id: int, season: int) -> pd.DataFrame:
    data = _af_get("/players/topscorers", {"league": league_af_id, "season": season})
    return _parse_af_players(data.get("response", [])) if data else pd.DataFrame()

@st.cache_data(ttl=3600)
def af_top_assists(league_af_id: int, season: int) -> pd.DataFrame:
    data = _af_get("/players/topassists", {"league": league_af_id, "season": season})
    return _parse_af_players(data.get("response", [])) if data else pd.DataFrame()

@st.cache_data(ttl=3600)
def af_top_cards(league_af_id: int, season: int) -> pd.DataFrame:
    data = _af_get("/players/topyellowcards", {"league": league_af_id, "season": season})
    return _parse_af_players(data.get("response", [])) if data else pd.DataFrame()

@st.cache_data(ttl=3600)
def af_team_players(team_id: int, league_af_id: int, season: int) -> pd.DataFrame:
    data = _af_get("/players", {"team": team_id, "league": league_af_id, "season": season})
    return _parse_af_players(data.get("response", [])) if data else pd.DataFrame()

@st.cache_data(ttl=3600)
def af_fixtures(league_af_id: int, season: int, status: str = "FT", limit: int = 30) -> pd.DataFrame:
    params = {"league": league_af_id, "season": season, "status": status}
    params["last" if status == "FT" else "next"] = limit
    data = _af_get("/fixtures", params)
    if not data:
        return pd.DataFrame()
    rows = []
    for m in data.get("response", []):
        fix = m["fixture"]; sc = m["goals"]
        try:
            dt = datetime.fromisoformat(fix["date"].replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
        except Exception:
            dt = fix["date"][:10]
        rows.append({
            "Data": dt, "Casa": m["teams"]["home"]["name"],
            "Fora": m["teams"]["away"]["name"],
            "Placar": f"{sc['home']} – {sc['away']}" if sc.get("home") is not None else "—",
            "GH": sc.get("home") or 0, "GA": sc.get("away") or 0,
            "Rodada": m["league"].get("round",""),
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED STANDINGS  (FD preferred, AF fallback)
# ─────────────────────────────────────────────────────────────────────────────
def get_standings(lg: dict, source: str, season: int) -> tuple[pd.DataFrame, str]:
    """Returns (df, source_used). Priority: FD > Bzzoiro > AF"""
    if source in ("football-data.org", "Automático") and HAS_FD and lg["fd_free"]:
        df = fd_standings(lg["fd_id"])
        if not df.empty:
            return df, "fd"
    if source in ("Bzzoiro", "Automático") and HAS_BZ and lg.get("bz_id"):
        df = bz_standings(lg["bz_id"])
        if not df.empty:
            return df, "bz"
    if source in ("API-Football", "Automático") and HAS_AF:
        df = af_standings(lg["af_id"], season)
        if not df.empty:
            return df, "af"
    return pd.DataFrame(), "none"

# ─────────────────────────────────────────────────────────────────────────────
# NO KEY SCREEN
# ─────────────────────────────────────────────────────────────────────────────
if not HAS_ANY:
    st.error("## 🔑 Nenhuma chave de API configurada")
    st.markdown("""
Configure ao menos **uma** das APIs gratuitas abaixo:

| API | Forças | Registro |
|-----|--------|---------|
| **football-data.org** | Classificação, partidas, artilheiros | [Registrar](https://www.football-data.org/client/register) |
| **Bzzoiro Sports Data** | Stats de jogadores, xG, xA, sem rate limit | [Registrar](https://sports.bzzoiro.com/register/) |
| **API-Football** | Stats avançadas de jogadores, métricas/90 | [Registrar](https://dashboard.api-football.com/register) |

**Streamlit Cloud → Settings → Secrets:**
```toml
FOOTBALL_DATA_KEY = "sua_chave_football_data"
BZZOIRO_KEY       = "sua_chave_bzzoiro"
API_FOOTBALL_KEY  = "sua_chave_api_football"
```
Você pode configurar uma, duas ou todas — o app se adapta automaticamente.
""")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Football Stats")
    st.markdown("---")

    # API source selector
    available_sources = []
    if HAS_FD:  available_sources.append("football-data.org")
    if HAS_BZ:  available_sources.append("Bzzoiro")
    if HAS_AF:  available_sources.append("API-Football")
    if len(available_sources) > 1:
        available_sources.insert(0, "Automático")

    source = st.selectbox(
        "🔌 Fonte de Dados",
        available_sources,
        help="Automático: football-data.org para classificação/partidas, Bzzoiro para jogadores (sem rate limit), API-Football como fallback.",
    )

    # Status pills
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        color = "#79c0ff" if HAS_FD else "#8b949e"
        icon  = "✅" if HAS_FD else "❌"
        st.markdown(f"<span style='color:{color};font-size:10px'>{icon} football-data</span>", unsafe_allow_html=True)
    with col_b:
        color = "#e3b341" if HAS_BZ else "#8b949e"
        icon  = "✅" if HAS_BZ else "❌"
        st.markdown(f"<span style='color:{color};font-size:10px'>{icon} bzzoiro</span>", unsafe_allow_html=True)
    with col_c:
        color = "#3fb950" if HAS_AF else "#8b949e"
        icon  = "✅" if HAS_AF else "❌"
        st.markdown(f"<span style='color:{color};font-size:10px'>{icon} api-football</span>", unsafe_allow_html=True)

    st.markdown("---")

    # Pages — hide player pages if no AF key
    pages_all = [
        "📊 Classificação",
        "📅 Partidas & Calendário",
        "👤 Jogadores",
        "🔀 Comparar Jogadores",
        "📈 Métricas Avançadas",
        "🏆 Comparar Times",
    ]
    pages_no_players = ["📊 Classificação", "📅 Partidas & Calendário", "🏆 Comparar Times"]
    has_players = HAS_AF or HAS_BZ or source in ("API-Football", "Bzzoiro")
    page_list = pages_all if has_players else pages_no_players

    page = st.radio("", page_list, label_visibility="collapsed")
    st.markdown("---")

    league_name  = st.selectbox("Liga", list(LEAGUES.keys()))
    lg           = LEAGUES[league_name]
    flag         = lg["flag"]
    league_short = league_name.split(" ", 1)[1]

    # ── Season selector ──────────────────────────────────────────────────────
    if HAS_AF:
        with st.spinner("Carregando temporadas..."):
            avail_seasons = af_available_seasons(lg["af_id"])

        if not avail_seasons:
            avail_seasons = list(range(lg["af_season_default"], lg["af_season_default"] - 6, -1))

        season_labels = [season_label(y, lg["af_season_type"]) for y in avail_seasons]

        # Pre-select the default/current season
        default_idx = 0
        for i, y in enumerate(avail_seasons):
            if y == lg["af_season_default"]:
                default_idx = i
                break

        selected_label = st.selectbox(
            "📅 Temporada",
            season_labels,
            index=default_idx,
            help="Selecione a temporada para visualizar as estatísticas.",
        )
        season = avail_seasons[season_labels.index(selected_label)]
        st.caption(f"API-Football · Temporada {selected_label}")
    else:
        # FD-only mode: no season picker (FD always returns current)
        season = lg["af_season_default"]
        st.caption(f"Temporada {season_label(season, lg['af_season_type'])}")
    # ─────────────────────────────────────────────────────────────────────────

    if not lg["fd_free"] and source == "football-data.org":
        st.warning("⚠️ Esta liga requer plano pago no football-data.org. Troque para API-Football.")

    st.markdown("---")
    st.caption("Cache: 1h por requisição")

# ─────────────────────────────────────────────────────────────────────────────
# SOURCE BADGE HELPER
# ─────────────────────────────────────────────────────────────────────────────
def badge(src: str):
    if src == "fd":
        st.markdown("<span class='source-badge-fd'>football-data.org</span>", unsafe_allow_html=True)
    elif src == "af":
        st.markdown("<span class='source-badge-af'>API-Football</span>", unsafe_allow_html=True)
    elif src == "bz":
        st.markdown("<span class='source-badge-af' style='background:#1a1a0d;color:#e3b341;border-color:#e3b341'>Bzzoiro Sports Data</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='source-badge-both'>Multi-fonte</span>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS: standings highlight & radar
# ─────────────────────────────────────────────────────────────────────────────
def hl_stand(row, total):
    if row["Pos"] <= 4:         return ["background:#0d2d0d;color:#3fb950"]*len(row)
    if row["Pos"] <= 6:         return ["background:#1a1a0d;color:#e3b341"]*len(row)
    if row["Pos"] >= total - 2: return ["background:#2d0d0d;color:#f85149"]*len(row)
    return [""]*len(row)

def radar_trace(name, vals, labels, color):
    return go.Scatterpolar(
        r=vals+[vals[0]], theta=labels+[labels[0]],
        fill="toself", name=name,
        fillcolor=f"{color}2a", line=dict(color=color, width=2),
    )

def polar_layout(fig):
    fig.update_layout(
        polar=dict(bgcolor="#161b22",
                   radialaxis=dict(visible=True, color="#8b949e"),
                   angularaxis=dict(color="#8b949e")),
        legend=dict(orientation="h", y=-0.12), height=460,
    )

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CLASSIFICAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def get_player_data(lg: dict, season: int, source: str) -> tuple[pd.DataFrame, str]:
    """Returns (df, src) — Bzzoiro preferred (no rate limit), AF as fallback."""
    if source in ("Bzzoiro", "Automático") and HAS_BZ and lg.get("bz_id"):
        df = bz_player_stats(lg["bz_id"])
        if not df.empty:
            return df, "bz"
    if source in ("API-Football", "Automático") and HAS_AF:
        df_s = af_top_scorers(lg["af_id"], season)
        df_a = af_top_assists(lg["af_id"], season)
        df = pd.concat([df_s, df_a]).drop_duplicates("Jogador").reset_index(drop=True)
        if not df.empty:
            return df, "af"
    return pd.DataFrame(), "none"

def get_fixture_data(lg: dict, season: int, source: str, finished: bool = True, limit: int = 30) -> tuple[pd.DataFrame, str]:
    """Returns (df, src) for match fixtures."""
    if source in ("Bzzoiro", "Automático") and HAS_BZ and lg.get("bz_id"):
        df = bz_matches(lg["bz_id"], finished=finished, limit=limit)
        if not df.empty:
            return df, "bz"
    if source in ("football-data.org", "Automático") and HAS_FD and lg["fd_free"]:
        status = "FINISHED" if finished else "SCHEDULED"
        df = fd_matches(lg["fd_id"], status=status, limit=limit)
        if not df.empty:
            return df, "fd"
    if source in ("API-Football", "Automático") and HAS_AF:
        status = "FT" if finished else "NS"
        df = af_fixtures(lg["af_id"], season, status=status, limit=limit)
        if not df.empty:
            return df, "af"
    return pd.DataFrame(), "none"

if "Classificação" in page:
    st.title(f"{flag} Classificação · {league_short}")
    with st.spinner("Carregando..."):
        df, src = get_standings(lg, source, season)
    if df.empty:
        st.info("Sem dados. Verifique sua chave e se a liga é suportada no plano gratuito."); st.stop()
    badge(src)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🥇 Líder",         df.iloc[0]["Time"],        f"{df.iloc[0]['Pts']} pts")
    c2.metric("⚽ Maior Ataque",   df.loc[df.GP.idxmax(),"Time"], f"{df.GP.max()} gols")
    c3.metric("🛡️ Melhor Defesa",  df.loc[df.GC.idxmin(),"Time"], f"{df.GC.min()} sofridos")
    c4.metric("📉 Lanterna",       df.iloc[-1]["Time"],       f"{df.iloc[-1]['Pts']} pts")

    st.markdown("<div class='section-header'>Tabela</div>", unsafe_allow_html=True)
    total = len(df)
    disp_cols = ["Pos","Time","PJ","V","E","D","GP","GC","SG","Pts","Forma"]
    st.dataframe(
        df[disp_cols].style.apply(lambda r: hl_stand(r, total), axis=1),
        use_container_width=True, hide_index=True,
    )
    st.caption("🟢 UEFA Groups · 🟡 Europa/Conference · 🔴 Rebaixamento")

    tab1, tab2, tab3 = st.tabs(["Gols & Defesa","Pontos","Vitórias × Derrotas"])
    with tab1:
        fig = go.Figure()
        fig.add_bar(name="Gols Marcados", x=df["Time"], y=df["GP"], marker_color="#238636")
        fig.add_bar(name="Gols Sofridos", x=df["Time"], y=df["GC"], marker_color="#da3633")
        fig.update_layout(barmode="group", xaxis_tickangle=-40, legend=dict(orientation="h"))
        st.plotly_chart(sf(fig), use_container_width=True)
    with tab2:
        fig2 = px.bar(df.sort_values("Pts",ascending=True), x="Pts", y="Time", orientation="h",
                      color="Pts", color_continuous_scale=["#0d2d5e","#1f6feb"])
        fig2.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
        st.plotly_chart(sf(fig2), use_container_width=True)
    with tab3:
        fig3 = px.scatter(df, x="D", y="V", size="Pts", text="Time",
                          color="Pts", color_continuous_scale="Greens",
                          labels={"D":"Derrotas","V":"Vitórias"})
        fig3.update_traces(textposition="top center")
        st.plotly_chart(sf(fig3), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PARTIDAS & CALENDÁRIO
# ─────────────────────────────────────────────────────────────────────────────
elif "Partidas" in page:
    st.title(f"📅 Partidas & Calendário · {league_short}")

    def _load_matches(status_fd, status_af, limit):
        if source in ("football-data.org","Automático") and HAS_FD and lg["fd_free"]:
            df = fd_matches(lg["fd_id"], status=status_fd, limit=limit)
            if not df.empty: return df, "fd"
        if source in ("API-Football","Automático") and HAS_AF:
            df = af_fixtures(lg["af_id"], season, status=status_af, limit=limit)
            if not df.empty: return df, "af"
        return pd.DataFrame(), "none"

    tab_r, tab_n = st.tabs(["✅ Resultados Recentes","🔜 Próximos Jogos"])

    with tab_r:
        with st.spinner("Buscando partidas..."):
            df_fix, src = get_fixture_data(lg, season, source, finished=True, limit=30)
        if df_fix.empty:
            st.info("Sem resultados.")
        else:
            badge(src)
            all_t = sorted(set(df_fix["Casa"].tolist()+df_fix["Fora"].tolist()))
            cf1,cf2 = st.columns([3,1])
            with cf1: tf = st.selectbox("Filtrar time",["Todos"]+all_t)
            with cf2:
                rds = sorted(df_fix["Rodada"].dropna().unique().tolist(),
                             key=lambda x: int(str(x).split()[-1]) if str(x).split()[-1].isdigit() else str(x))
                rf = st.selectbox("Rodada",["Todas"]+[str(r) for r in rds])
            dv = df_fix.copy()
            if tf != "Todos": dv = dv[(dv["Casa"]==tf)|(dv["Fora"]==tf)]
            if rf != "Todas": dv = dv[dv["Rodada"].astype(str)==rf]
            st.dataframe(dv[["Data","Rodada","Casa","Placar","Fora"]],
                         use_container_width=True, hide_index=True)

            st.markdown("<div class='section-header'>Gols por Rodada</div>", unsafe_allow_html=True)
            df_fix["Total"] = df_fix["GH"] + df_fix["GA"]
            agg = df_fix.groupby("Rodada").agg(Gols=("Total","sum"),
                                                Partidas=("Total","count")).reset_index()
            agg["Média"] = (agg["Gols"]/agg["Partidas"]).round(2)
            fig_rnd = go.Figure()
            fig_rnd.add_bar(x=agg["Rodada"], y=agg["Gols"], name="Total", marker_color="#238636")
            fig_rnd.add_scatter(x=agg["Rodada"], y=agg["Média"], name="Média/jogo",
                                mode="lines+markers", line=dict(color="#e3b341",width=2))
            fig_rnd.update_layout(legend=dict(orientation="h"))
            st.plotly_chart(sf(fig_rnd), use_container_width=True)

    with tab_n:
        with st.spinner("Buscando agenda..."):
            df_next, src2 = get_fixture_data(lg, season, source, finished=False, limit=20)
        if df_next.empty:
            st.info("Nenhuma partida agendada.")
        else:
            badge(src2)
            at = sorted(set(df_next["Casa"].tolist()+df_next["Fora"].tolist()))
            tu = st.selectbox("Filtrar time",["Todos"]+at)
            dn = df_next.copy()
            if tu != "Todos": dn = dn[(dn["Casa"]==tu)|(dn["Fora"]==tu)]
            st.dataframe(dn[["Data","Rodada","Casa","Fora"]],
                         use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: JOGADORES
# ─────────────────────────────────────────────────────────────────────────────
elif "Jogadores" in page and "Comparar" not in page:
    st.title(f"👤 Estatísticas de Jogadores · {league_short}")
    badge("af")

    sub = st.radio("Ranking por",
                   ["⚽ Artilheiros","🎯 Assistências","🟨 Cartões Amarelos"],
                   horizontal=True)

    with st.spinner("Carregando jogadores..."):
        if "Artilheiros" in sub:
            df_p = af_top_scorers(lg["af_id"], season); mc = "Gols"
        elif "Assistências" in sub:
            df_p = af_top_assists(lg["af_id"], season); mc = "Assistências"
        else:
            df_p = af_top_cards(lg["af_id"], season); mc = "Amarelos"

    if df_p.empty:
        st.info("Sem dados. Verifique a chave da API-Football."); st.stop()

    # Pódio
    st.markdown("<div class='section-header'>Pódio</div>", unsafe_allow_html=True)
    for i, (col, medal) in enumerate(zip(st.columns(3), ["🥇","🥈","🥉"])):
        if i < len(df_p):
            r = df_p.iloc[i]
            col.metric(f"{medal} {r['Jogador']}", f"{r[mc]} {mc.lower()}",
                       f"{r['Time']} · {r['Minutos']} min")

    # Bar chart
    st.markdown("<div class='section-header'>Ranking Completo</div>", unsafe_allow_html=True)
    top20 = df_p.head(20)
    fig = px.bar(top20, x="Jogador", y=mc, color="G+A",
                 color_continuous_scale=["#0d4429","#3fb950"],
                 text=mc, hover_data=["Time","Jogos","Minutos","Nota"])
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(sf(fig), use_container_width=True)

    # Tabs
    t1,t2,t3,t4 = st.tabs(["📋 Tabela","⚡ Gols × Assistências","🎯 Chutes & Conversão","🛡️ Defensivo"])

    with t1:
        base_cols = ["Jogador","Time","Posição","Jogos","Minutos","Nota","Gols","Assistências",
                     "G+A","Gols/90","Assists/90","G+A/90","Chutes","Conversão (%)","Amarelos","Vermelhos"]
        xg_cols = ["xG","xA","xG+xA"] if (src_p == "bz" and "xG" in df_p.columns) else []
        cols = base_cols[:9] + xg_cols + base_cols[9:]
        def hl_t(row):
            if row.name==0: return ["background:#0d4429;color:#56d364"]*len(row)
            if row.name==1: return ["background:#0d2d1a;color:#3fb950"]*len(row)
            return [""]*len(row)
        st.dataframe(df_p[cols].style.apply(hl_t,axis=1),
                     use_container_width=True, hide_index=True)

    with t2:
        if df_p["Assistências"].sum() > 0:
            fig2 = px.scatter(df_p.head(30), x="Assistências", y="Gols",
                              text="Jogador", size="Jogos",
                              color="Nota", color_continuous_scale="RdYlGn",
                              hover_data=["Time","Minutos","Gols/90"])
            fig2.update_traces(textposition="top center")
            # Quadrants
            mx, my = df_p["Assistências"].median(), df_p["Gols"].median()
            fig2.add_vline(x=mx, line_dash="dot", line_color="#8b949e")
            fig2.add_hline(y=my, line_dash="dot", line_color="#8b949e")
            st.plotly_chart(sf(fig2,550), use_container_width=True)

    with t3:
        df_sh = df_p[df_p["Chutes"]>0].copy()
        if not df_sh.empty:
            fig3 = px.scatter(df_sh.head(30), x="Chutes", y="Gols",
                              size="Conversão (%)", text="Jogador",
                              color="Conversão (%)",
                              color_continuous_scale=["#da3633","#e3b341","#238636"],
                              hover_data=["Time","Chutes no Alvo"])
            fig3.update_traces(textposition="top center")
            fig3.add_hline(y=df_sh["Gols"].mean(), line_dash="dot",
                           line_color="#8b949e", annotation_text="Média")
            st.plotly_chart(sf(fig3,520), use_container_width=True)

    with t4:
        def_cols = ["Jogador","Time","Jogos","Desarmes","Interceptações",
                    "Bloqueios","Desarmes/90","Faltas Cometidas","Faltas Sofridas"]
        df_def = df_p[df_p["Desarmes"]>0].sort_values("Desarmes",ascending=False)
        if not df_def.empty:
            fig4 = px.bar(df_def.head(15), x="Desarmes", y="Jogador",
                          orientation="h", color="Desarmes/90",
                          color_continuous_scale=["#0d2d5e","#1f6feb"],
                          hover_data=["Time","Interceptações"])
            fig4.update_layout(yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(sf(fig4), use_container_width=True)
            st.dataframe(df_def[def_cols].head(15),
                         use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: COMPARAR JOGADORES
# ─────────────────────────────────────────────────────────────────────────────
elif "Comparar Jogadores" in page:
    st.title(f"🔀 Comparar Jogadores · {league_short}")
    with st.spinner("Carregando jogadores..."):
        df_all, src_cmp = get_player_data(lg, season, source)
        badge(src_cmp)

    if df_all.empty:
        st.info("Sem dados de jogadores."); st.stop()

    pnames = df_all["Jogador"].tolist()
    c1,c2 = st.columns(2)
    with c1: p1 = st.selectbox("Jogador 1", pnames, index=0)
    with c2: p2 = st.selectbox("Jogador 2", pnames, index=min(1,len(pnames)-1))

    r1 = df_all[df_all["Jogador"]==p1].iloc[0]
    r2 = df_all[df_all["Jogador"]==p2].iloc[0]

    kpi_keys = ["Gols","Assistências","G+A","Gols/90","G+A/90",
                "Chutes","Conversão (%)","Passes-Chave","Desarmes","Amarelos"]

    # KPIs 3 col
    st.markdown(f"<div class='section-header'>{p1} vs {p2}</div>", unsafe_allow_html=True)
    ca,cb,cc = st.columns([5,1,5])
    with ca:
        st.markdown(f"#### {r1['Time']}")
        for k in kpi_keys:
            st.metric(k, r1[k])
    with cb:
        st.markdown("#### &nbsp;", unsafe_allow_html=True)
        for _ in kpi_keys:
            st.markdown("<div style='text-align:center;padding:8px 0;color:#8b949e'>⟺</div>",
                        unsafe_allow_html=True)
    with cc:
        st.markdown(f"#### {r2['Time']}")
        for k in kpi_keys:
            v1,v2 = float(r1[k]), float(r2[k])
            delta = round(v2-v1,2)
            st.metric(k, r2[k], delta=delta if delta != 0 else None)

    # Radar
    st.markdown("<div class='section-header'>Radar Comparativo</div>", unsafe_allow_html=True)
    rk = ["Gols","Assistências","Chutes","Passes-Chave","Desarmes",
          "Gols/90","G+A/90","Conversão (%)","Precisão Pass (%)","Drible (%)"]
    rv1 = [float(r1[k]) for k in rk]
    rv2 = [float(r2[k]) for k in rk]
    fig_r = go.Figure([radar_trace(p1,rv1,rk,"#3fb950"), radar_trace(p2,rv2,rk,"#1f6feb")])
    polar_layout(fig_r)
    st.plotly_chart(sf(fig_r), use_container_width=True)

    # Barras
    st.markdown("<div class='section-header'>Barras Comparativas</div>", unsafe_allow_html=True)
    bk = ["Gols","Assistências","G+A","Chutes","Passes-Chave","Desarmes","Amarelos","Jogos"]
    fig_b = go.Figure([
        go.Bar(name=p1, x=bk, y=[float(r1[k]) for k in bk], marker_color="#3fb950"),
        go.Bar(name=p2, x=bk, y=[float(r2[k]) for k in bk], marker_color="#1f6feb"),
    ])
    fig_b.update_layout(barmode="group", xaxis_tickangle=-25, legend=dict(orientation="h"))
    st.plotly_chart(sf(fig_b), use_container_width=True)

    # Pizza distribuição de stats
    st.markdown("<div class='section-header'>Distribuição G / A / Outros Chutes</div>", unsafe_allow_html=True)
    col_pie1, col_pie2 = st.columns(2)
    for col, rr, name in [(col_pie1,r1,p1),(col_pie2,r2,p2)]:
        with col:
            gols_val   = float(rr["Gols"])
            assists_val= float(rr["Assistências"])
            outros_ch  = max(0, float(rr["Chutes"]) - gols_val)
            fig_pi = px.pie(
                values=[gols_val, assists_val, outros_ch],
                names=["Gols","Assistências","Chutes (outros)"],
                title=name,
                color_discrete_sequence=["#238636","#1f6feb","#8b949e"],
                hole=0.4,
            )
            st.plotly_chart(sf(fig_pi), use_container_width=True)

    # Tabela diff
    st.markdown("<div class='section-header'>Diferença por Métrica</div>", unsafe_allow_html=True)
    diff_rows = []
    for k in kpi_keys:
        v1,v2 = r1[k],r2[k]
        try:
            diff  = round(float(v1)-float(v2),2)
            melhor= p1 if diff>0 else (p2 if diff<0 else "Igual")
            if k in ("Amarelos","Vermelhos"):
                melhor = p1 if float(v1)<float(v2) else (p2 if float(v2)<float(v1) else "Igual")
        except Exception:
            diff,melhor = "—","—"
        diff_rows.append({"Métrica":k, p1:v1, p2:v2, "Diferença":diff, "Melhor":melhor})
    st.dataframe(pd.DataFrame(diff_rows), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: MÉTRICAS AVANÇADAS
# ─────────────────────────────────────────────────────────────────────────────
elif "Métricas" in page:
    st.title(f"📈 Métricas Avançadas · {league_short}")
    st.caption("Estatísticas combinadas calculadas a partir dos minutos em campo (mín. 200 min).")
    with st.spinner("Carregando..."):
        df_raw, src_met = get_player_data(lg, season, source)
        badge(src_met)

    df_all = df_raw[df_raw["Minutos"] >= 200].copy() if not df_raw.empty else pd.DataFrame()
    if df_all.empty:
        st.info("Sem dados suficientes. Configure BZZOIRO_KEY ou API_FOOTBALL_KEY."); st.stop()

    tab1,tab2,tab3,tab4 = st.tabs([
        "🎯 Por 90 Minutos","📊 Distribuições","🔥 Heatmap","📐 Correlações"
    ])

    with tab1:
        col_l,col_r = st.columns(2)
        with col_l:
            st.markdown("<div class='section-header'>Gols/90 min</div>", unsafe_allow_html=True)
            top = df_all.nlargest(15,"Gols/90")
            fig1 = px.bar(top, x="Gols/90", y="Jogador", orientation="h",
                          color="Gols/90", color_continuous_scale=["#0d4429","#3fb950"],
                          text="Gols/90", hover_data=["Time","Gols","Minutos"])
            fig1.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
            st.plotly_chart(sf(fig1), use_container_width=True)
        with col_r:
            st.markdown("<div class='section-header'>G+A/90 min</div>", unsafe_allow_html=True)
            top2 = df_all.nlargest(15,"G+A/90")
            fig2 = px.bar(top2, x="G+A/90", y="Jogador", orientation="h",
                          color="G+A/90", color_continuous_scale=["#0d2d5e","#1f6feb"],
                          text="G+A/90")
            fig2.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
            st.plotly_chart(sf(fig2), use_container_width=True)

        st.markdown("<div class='section-header'>Taxa de Conversão (%) — mín. 10 chutes</div>", unsafe_allow_html=True)
        df_conv = df_all[df_all["Chutes"]>=10].nlargest(15,"Conversão (%)")
        if not df_conv.empty:
            fig3 = px.bar(df_conv, x="Conversão (%)", y="Jogador", orientation="h",
                          color="Conversão (%)", color_continuous_scale=["#3d1a00","#e3b341"],
                          text="Conversão (%)")
            fig3.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
            st.plotly_chart(sf(fig3), use_container_width=True)

        st.markdown("<div class='section-header'>Minutos × Gols  (tamanho = G+A/90, cor = Nota)</div>", unsafe_allow_html=True)
        df_sc = df_all[df_all["Nota"].notna()].copy()
        if not df_sc.empty:
            fig4 = px.scatter(df_sc, x="Minutos", y="Gols", size="G+A/90",
                              text="Jogador", color="Nota",
                              color_continuous_scale="RdYlGn",
                              hover_data=["Time","Gols/90","Assistências"])
            fig4.update_traces(textposition="top center")
            st.plotly_chart(sf(fig4,560), use_container_width=True)

        # xG section — only available from Bzzoiro
        if src_met == "bz" and "xG" in df_all.columns and df_all["xG"].sum() > 0:
            st.markdown("<div class='section-header'>xG vs Gols Reais (quem superou as expectativas?)</div>", unsafe_allow_html=True)
            df_xg = df_all[df_all["xG"] > 0].copy()
            df_xg["Diferença xG"] = df_xg["Gols"] - df_xg["xG"]
            fig_xg = px.scatter(df_xg.head(30), x="xG", y="Gols",
                                text="Jogador", color="Diferença xG",
                                color_continuous_scale="RdYlGn",
                                hover_data=["Time","xA","G+A"])
            fig_xg.add_shape(type="line", x0=0, y0=0,
                             x1=df_xg["xG"].max(), y1=df_xg["xG"].max(),
                             line=dict(color="#8b949e", dash="dot"))
            fig_xg.add_annotation(text="Linha xG esperado", x=df_xg["xG"].max()*0.8,
                                   y=df_xg["xG"].max()*0.75, showarrow=False,
                                   font=dict(color="#8b949e", size=11))
            fig_xg.update_traces(textposition="top center")
            st.plotly_chart(sf(fig_xg, 520), use_container_width=True)

    with tab2:
        col_l2,col_r2 = st.columns(2)
        with col_l2:
            st.markdown("<div class='section-header'>Posições — Top Jogadores</div>", unsafe_allow_html=True)
            pc = df_all["Posição"].value_counts().reset_index()
            pc.columns = ["Posição","Count"]
            fig_pie = px.pie(pc, values="Count", names="Posição", hole=0.4,
                             color_discrete_sequence=["#238636","#1f6feb","#e3b341","#da3633","#8957e5"])
            fig_pie.update_traces(textfont_size=13)
            st.plotly_chart(sf(fig_pie), use_container_width=True)
        with col_r2:
            st.markdown("<div class='section-header'>Gols/90 por Posição (Boxplot)</div>", unsafe_allow_html=True)
            fig_box = px.box(df_all[df_all["Gols/90"]>0], x="Posição", y="Gols/90",
                             color="Posição",
                             color_discrete_sequence=["#238636","#1f6feb","#e3b341","#da3633","#8957e5"])
            st.plotly_chart(sf(fig_box), use_container_width=True)

        st.markdown("<div class='section-header'>Distribuição de G+A/90 (Histograma)</div>", unsafe_allow_html=True)
        fig_hist = px.histogram(df_all[df_all["G+A/90"]>0], x="G+A/90",
                                nbins=20, color_discrete_sequence=["#238636"])
        fig_hist.update_layout(bargap=0.1)
        st.plotly_chart(sf(fig_hist), use_container_width=True)

    with tab3:
        st.markdown("<div class='section-header'>Heatmap de Estatísticas (Top 20 por G+A)</div>", unsafe_allow_html=True)
        hcols = ["Gols","Assistências","G+A","Gols/90","G+A/90",
                 "Conversão (%)","Chutes/90","Passes-Chave","Desarmes/90","Drible (%)"]
        df_h = df_all.nlargest(20,"G+A")[["Jogador"]+hcols].set_index("Jogador").astype(float)
        df_n = (df_h - df_h.min()) / (df_h.max() - df_h.min() + 1e-9)
        fig_h = px.imshow(df_n.T, color_continuous_scale="Greens", aspect="auto",
                          labels=dict(x="Jogador", y="Métrica", color="Norm."))
        fig_h.update_layout(height=420)
        st.plotly_chart(sf(fig_h), use_container_width=True)

    with tab4:
        st.markdown("<div class='section-header'>Correlação entre Métricas</div>", unsafe_allow_html=True)
        corr_cols = ["Gols","Assistências","Gols/90","Chutes","Conversão (%)",
                     "Passes-Chave","Desarmes","Minutos","Nota"]
        df_corr = df_all[corr_cols].dropna().corr()
        fig_corr = px.imshow(df_corr, color_continuous_scale="RdBu", zmin=-1, zmax=1,
                             text_auto=".2f", aspect="auto")
        fig_corr.update_layout(height=500)
        st.plotly_chart(sf(fig_corr), use_container_width=True)

        st.markdown("<div class='section-header'>Scatter Livre — Escolha os Eixos</div>", unsafe_allow_html=True)
        num_cols = [c for c in df_all.columns if df_all[c].dtype in ["float64","int64"]]
        cx,cy,cz = st.columns(3)
        with cx: x_ax = st.selectbox("Eixo X", num_cols, index=num_cols.index("Chutes") if "Chutes" in num_cols else 0)
        with cy: y_ax = st.selectbox("Eixo Y", num_cols, index=num_cols.index("Gols") if "Gols" in num_cols else 1)
        with cz: col_ax= st.selectbox("Cor",   num_cols, index=num_cols.index("Nota") if "Nota" in num_cols else 2)
        fig_free = px.scatter(df_all.dropna(subset=[x_ax,y_ax,col_ax]),
                              x=x_ax, y=y_ax, color=col_ax, text="Jogador",
                              color_continuous_scale="RdYlGn",
                              hover_data=["Time","Minutos"])
        fig_free.update_traces(textposition="top center")
        st.plotly_chart(sf(fig_free,500), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: COMPARAR TIMES
# ─────────────────────────────────────────────────────────────────────────────
elif "Comparar Times" in page:
    st.title(f"🏆 Comparar Times · {league_short}")

    with st.spinner("Carregando classificação..."):
        df_st, src = get_standings(lg, source, season)
    if df_st.empty:
        st.info("Sem dados."); st.stop()
    badge(src)

    tnames = df_st["Time"].tolist()
    c1,c2 = st.columns(2)
    with c1: t1 = st.selectbox("Time 1", tnames, index=0)
    with c2: t2 = st.selectbox("Time 2", tnames, index=min(1,len(tnames)-1))

    r1 = df_st[df_st["Time"]==t1].iloc[0]
    r2 = df_st[df_st["Time"]==t2].iloc[0]

    mets = [("Pontos","Pts"),("Vitórias","V"),("Empates","E"),("Derrotas","D"),
            ("Gols Marcados","GP"),("Gols Sofridos","GC"),("Saldo","SG")]

    tab1,tab2,tab3 = st.tabs(["Barras","Radar","Tabela"])
    with tab1:
        fig = go.Figure([
            go.Bar(name=t1, x=[m[0] for m in mets], y=[int(r1[m[1]]) for m in mets], marker_color="#3fb950"),
            go.Bar(name=t2, x=[m[0] for m in mets], y=[int(r2[m[1]]) for m in mets], marker_color="#1f6feb"),
        ])
        fig.update_layout(barmode="group", legend=dict(orientation="h"))
        st.plotly_chart(sf(fig), use_container_width=True)
    with tab2:
        rm = [("Vitórias","V"),("Gols Marcados","GP"),("Saldo","SG"),("Pontos","Pts"),("Jogos","PJ")]
        rl1=[int(r1[m[1]]) for m in rm]; rl2=[int(r2[m[1]]) for m in rm]; lbls=[m[0] for m in rm]
        fig_r = go.Figure([radar_trace(t1,rl1,lbls,"#3fb950"),radar_trace(t2,rl2,lbls,"#1f6feb")])
        polar_layout(fig_r)
        st.plotly_chart(sf(fig_r), use_container_width=True)
    with tab3:
        rows = []
        for label,key in mets:
            v1,v2 = int(r1[key]),int(r2[key])
            melhor = (t1 if v1<v2 else (t2 if v2<v1 else "Igual")) if key in ("GC","D") \
                     else (t1 if v1>v2 else (t2 if v2>v1 else "Igual"))
            rows.append({"Métrica":label,t1:v1,t2:v2,"Melhor":melhor})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Jogadores do time (apenas se AF disponível)
    if HAS_AF or HAS_BZ:
        lbl = "Bzzoiro Sports Data" if (HAS_BZ and source != "API-Football") else "API-Football"
        st.markdown(f"<div class='section-header'>Jogadores do Time ({lbl})</div>", unsafe_allow_html=True)
        badge("bz" if (HAS_BZ and source != "API-Football") else "af")
        team_sel = st.selectbox("Ver jogadores de",[t1,t2])
        tid_col = "team_id_af" if "team_id_af" in df_st.columns else ("team_id_fd" if "team_id_fd" in df_st.columns else None)

        if tid_col:
            tid = int(df_st[df_st["Time"]==team_sel].iloc[0][tid_col])
            # if came from FD we need AF team id — try lookup via standings
            if src == "fd":
                df_af_tmp = af_standings(lg["af_id"], season)
                if not df_af_tmp.empty:
                    row_tmp = df_af_tmp[df_af_tmp["Time"].str.contains(team_sel.split()[0], case=False, na=False)]
                    if not row_tmp.empty:
                        tid = int(row_tmp.iloc[0]["team_id_af"])
            with st.spinner(f"Carregando jogadores de {team_sel}..."):
                df_tp = af_team_players(tid, lg["af_id"], season)
            if not df_tp.empty:
                show = ["Jogador","Posição","Jogos","Minutos","Gols","Assistências",
                        "G+A","Gols/90","G+A/90","Nota","Amarelos","Vermelhos"]
                st.dataframe(df_tp[show].sort_values("G+A",ascending=False),
                             use_container_width=True, hide_index=True)
                fig_tp = px.bar(df_tp.nlargest(12,"G+A"), x="Jogador",
                                y=["Gols","Assistências"], barmode="stack",
                                color_discrete_map={"Gols":"#3fb950","Assistências":"#1f6feb"},
                                text_auto=True)
                fig_tp.update_layout(xaxis_tickangle=-30, legend=dict(orientation="h"))
                st.plotly_chart(sf(fig_tp), use_container_width=True)
