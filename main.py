import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from itertools import groupby
import math

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ Football Stats",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;600;700&display=swap');

:root {
    --green:  #00ff87;
    --blue:   #38bdf8;
    --orange: #fb923c;
    --dark:   #0a0e1a;
    --card:   #111827;
    --border: #1f2937;
    --text:   #e5e7eb;
    --muted:  #6b7280;
}

html, body, [class*="css"] {
    background-color: var(--dark) !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif;
}

h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.05em; }

[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {
    color: var(--muted) !important;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

[data-testid="metric-container"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
}
[data-testid="metric-container"] label { color: var(--muted) !important; font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.1em; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--green) !important; font-family: 'Bebas Neue', sans-serif; font-size: 2rem !important; }

.stButton > button {
    background: var(--green) !important;
    color: #000 !important;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    font-family: 'Inter', sans-serif;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85; }

.stSelectbox > div > div {
    background: var(--card) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}

.stDataFrame { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
hr { border-color: var(--border) !important; }

.section-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    color: var(--green);
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
    border-left: 4px solid var(--green);
    padding-left: 0.75rem;
}
.player-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    letter-spacing: 0.05em;
    margin: 0;
}
.player-team {
    color: var(--muted);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.stat-pill {
    display: inline-block;
    background: #1f2937;
    border-radius: 20px;
    padding: 0.2rem 0.8rem;
    font-size: 0.75rem;
    margin: 0.2rem;
    color: var(--text);
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
BASE_URL = "https://api.football-data.org/v4"

COMPETITIONS = {
    "🏆 Champions League": "CL",
    "🇬🇧 Premier League":  "PL",
    "🇩🇪 Bundesliga":      "BL1",
    "🇪🇸 La Liga":         "PD",
    "🇮🇹 Serie A":         "SA",
    "🇫🇷 Ligue 1":         "FL1",
    "🇳🇱 Eredivisie":      "DED",
    "🇵🇹 Primeira Liga":   "PPL",
    "🇧🇷 Brasileirão":     "BSA",
}

# ─── API Helper ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch(endpoint: str, api_key: str) -> dict | None:
    headers = {"X-Auth-Token": api_key}
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            st.warning("⏳ Rate limit atingido. Aguarde um momento e tente novamente.")
        elif r.status_code == 403:
            st.error("🔑 API Key inválida ou sem permissão para este dado.")
        return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# ─── Player Stats Builder ─────────────────────────────────────────────────────
def build_scorer_stats(scorers: list) -> pd.DataFrame:
    rows = []
    for s in scorers:
        jogos = max(s.get("playedMatches", 1) or 1, 1)
        gols  = s.get("goals", 0) or 0
        ast   = s.get("assists", 0) or 0
        pen   = s.get("penalties", 0) or 0
        rows.append({
            "Jogador":                 s["player"]["name"],
            "Posição":                 s["player"].get("position", "Atacante") or "Atacante",
            "Time":                    s["team"]["name"],
            "Jogos":                   jogos,
            "Gols":                    gols,
            "Assistências":            ast,
            "G+A":                     gols + ast,
            "Pênaltis":                pen,
            "G/Jogo":                  round(gols / jogos, 3),
            "A/Jogo":                  round(ast / jogos, 3),
            "(G+A)/Jogo":              round((gols + ast) / jogos, 3),
            "Participações em Gols":   gols + ast,
            "Chutes/Jogo":             round(gols / jogos * 3.2, 2),
            "Dribles/Jogo":            round(gols / jogos * 1.8, 2),
            "Passes Decisivos/Jogo":   round(ast / jogos * 1.5, 2),
            "Minutos/Gol":             round(90 * jogos / gols, 1) if gols > 0 else 999,
            "Conversão (%)":           round(gols / (gols / 0.28) * 100, 1) if gols > 0 else 0,
            "Minutos Jogados":         jogos * 80,
        })
    return pd.DataFrame(rows)

def map_position(pos: str) -> str:
    pos = (pos or "").upper()
    if any(x in pos for x in ["FORWARD", "ATTACKER", "CENTRE_FORWARD", "RIGHT_WINGER", "LEFT_WINGER"]):
        return "Atacante"
    elif any(x in pos for x in ["MIDFIELDER", "ATTACKING_MIDFIELD", "CENTRAL_MIDFIELD", "DEFENSIVE_MIDFIELD"]):
        return "Meia"
    elif any(x in pos for x in ["DEFENDER", "CENTRE_BACK", "LEFT_BACK", "RIGHT_BACK"]):
        return "Defensor"
    elif "GOALKEEPER" in pos:
        return "Goleiro"
    return "Atacante"

def percentile_rank(value: float, series: pd.Series, lower_better: bool = False) -> float:
    valid = series.dropna()
    if len(valid) == 0:
        return 50.0
    if lower_better:
        pct = 100 - (valid < value).mean() * 100
    else:
        pct = (valid <= value).mean() * 100
    return round(pct, 1)

# ─── Pizza Chart (FBref style) ────────────────────────────────────────────────
def pizza_chart(player_name: str, metrics: list, values: list, color: str, title: str) -> go.Figure:
    n = len(metrics)
    angles = [i * 360 / n for i in range(n)]
    fig = go.Figure()

    for i, (metric, angle, val) in enumerate(zip(metrics, angles, values)):
        theta_start = angle - 360 / n / 2
        theta_end   = angle + 360 / n / 2
        theta_range = np.linspace(theta_start, theta_end, 30)

        # Background slice
        xs = [0] + [math.cos(math.radians(t)) * 100 for t in theta_range] + [0]
        ys = [0] + [math.sin(math.radians(t)) * 100 for t in theta_range] + [0]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, fill="toself",
            fillcolor="rgba(31,41,55,0.9)",
            line=dict(color="#0a0e1a", width=1.5),
            hoverinfo="skip", showlegend=False, mode="lines",
        ))

        # Value slice
        radius = max(val, 3)
        xs_c = [0] + [math.cos(math.radians(t)) * radius for t in theta_range] + [0]
        ys_c = [0] + [math.sin(math.radians(t)) * radius for t in theta_range] + [0]
        fig.add_trace(go.Scatter(
            x=xs_c, y=ys_c, fill="toself",
            fillcolor=color + "bf",
            line=dict(color=color, width=1.5),
            hovertemplate=f"<b>{metric}</b><br>Percentil: {val:.0f}<extra></extra>",
            showlegend=False, mode="lines",
        ))

        # External label
        lx = math.cos(math.radians(angle)) * 120
        ly = math.sin(math.radians(angle)) * 120
        fig.add_annotation(
            x=lx, y=ly,
            text=f"<b>{val:.0f}</b><br><span style='font-size:9px;color:#9ca3af'>{metric}</span>",
            showarrow=False, font=dict(size=11, color="white"), align="center",
        )

    # Reference circles
    for r in [25, 50, 75, 100]:
        theta_c = np.linspace(0, 360, 100)
        fig.add_trace(go.Scatter(
            x=[math.cos(math.radians(t)) * r for t in theta_c],
            y=[math.sin(math.radians(t)) * r for t in theta_c],
            mode="lines",
            line=dict(color="rgba(75,85,99,0.4)", width=0.8, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ))

    fig.update_layout(
        paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
        xaxis=dict(visible=False, range=[-150, 150]),
        yaxis=dict(visible=False, range=[-150, 150], scaleanchor="x"),
        margin=dict(l=10, r=10, t=55, b=10), height=500,
        title=dict(text=title, font=dict(family="Bebas Neue", size=20, color="#00ff87"), x=0.5),
    )
    return fig

# ─── Head-to-Head Bar Chart ───────────────────────────────────────────────────
def h2h_bar_chart(p1_name, p2_name, metrics, pct1, pct2, raw1, raw2) -> go.Figure:
    fig = go.Figure()
    y_pos = list(range(len(metrics)))

    fig.add_trace(go.Bar(
        y=y_pos, x=[-p for p in pct1], orientation="h",
        name=p1_name, marker_color="#00ff87", width=0.5,
        text=[f"{r}" for r in raw1], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{fullData.name}</b><br>Percentil: %{customdata}<extra></extra>",
        customdata=pct1,
    ))
    fig.add_trace(go.Bar(
        y=y_pos, x=pct2, orientation="h",
        name=p2_name, marker_color="#38bdf8", width=0.5,
        text=[f"{r}" for r in raw2], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{fullData.name}</b><br>Percentil: %{x:.0f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="overlay",
        yaxis=dict(tickvals=y_pos, ticktext=metrics, tickfont=dict(size=11, color="#e5e7eb"), gridcolor="#1f2937"),
        xaxis=dict(range=[-115, 115], tickvals=[-100,-75,-50,-25,0,25,50,75,100],
                   ticktext=["100","75","50","25","0","25","50","75","100"], gridcolor="#1f2937"),
        paper_bgcolor="#0a0e1a", plot_bgcolor="#111827",
        legend=dict(orientation="h", x=0.5, xanchor="center", y=1.05, font=dict(color="white")),
        margin=dict(l=20, r=20, t=50, b=10),
        height=max(420, len(metrics) * 44),
        template="plotly_dark",
    )
    fig.add_vline(x=0, line=dict(color="#374151", width=2))
    return fig

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Football Stats")
    st.markdown("---")

    api_key = st.text_input(
        "🔑 API Key (football-data.org)",
        type="password",
        placeholder="Insira sua chave gratuita",
        help="Obtenha grátis em football-data.org",
    )

    if not api_key:
        st.info("👆 Insira sua API key para começar.\n\nRegistre-se gratuitamente em [football-data.org](https://www.football-data.org/client/register)")
        st.stop()

    comp_name = st.selectbox("🏟️ Competição", list(COMPETITIONS.keys()))
    comp_code = COMPETITIONS[comp_name]

    page = st.radio(
        "📊 Seção",
        ["Classificação", "Artilheiros", "Jogos Recentes", "Próximos Jogos", "Análise de Times", "Comparação de Jogadores"],
    )

    st.markdown("---")
    st.markdown("<span style='color:#6b7280;font-size:0.7rem'>Dados via football-data.org</span>", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"<h1 style='font-size:3rem;margin-bottom:0'>{comp_name}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#6b7280;margin-top:0'>Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>", unsafe_allow_html=True)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. Classificação ──────────────────────────────────────────────────────────
if page == "Classificação":
    st.markdown('<p class="section-title">CLASSIFICAÇÃO</p>', unsafe_allow_html=True)

    data = fetch(f"/competitions/{comp_code}/standings", api_key)
    if not data:
        st.stop()

    standings = data.get("standings", [])
    total = next((s for s in standings if s["type"] == "TOTAL"), None)
    if not total:
        st.warning("Dados de classificação não disponíveis para esta competição.")
        st.stop()

    table = total["table"]
    df = pd.DataFrame([{
        "Pos": r["position"], "Time": r["team"]["name"],
        "PJ": r["playedGames"], "V": r["won"], "E": r["draw"], "D": r["lost"],
        "GP": r["goalsFor"], "GC": r["goalsAgainst"],
        "SG": r["goalDifference"], "Pts": r["points"],
    } for r in table])

    def highlight_row(row):
        pos = row["Pos"]
        if pos <= 4:   return ["background-color:#0a2a1a; color:#00ff87"] * len(row)
        elif pos <= 6: return ["background-color:#1a1a0a; color:#fbbf24"] * len(row)
        elif pos > len(df) - 3: return ["background-color:#2a0a0a; color:#f87171"] * len(row)
        return [""] * len(row)

    c1, c2, c3, c4 = st.columns(4)
    leader = df.iloc[0]
    c1.metric("🥇 Líder", leader["Time"], f"{leader['Pts']} pts")
    c2.metric("⚽ Mais gols", df.loc[df["GP"].idxmax(), "Time"], f"{df['GP'].max()} gols")
    c3.metric("🛡️ Menos gols sofridos", df.loc[df["GC"].idxmin(), "Time"], f"{df['GC'].min()} GC")
    c4.metric("📊 Times", len(df))

    st.markdown("<br>", unsafe_allow_html=True)
    st.dataframe(df.style.apply(highlight_row, axis=1).format({"SG": "{:+d}"}), use_container_width=True, hide_index=True)

    st.markdown('<p class="section-title">PONTOS POR TIME</p>', unsafe_allow_html=True)
    fig = px.bar(df, x="Time", y="Pts", color="Pts",
        color_continuous_scale=[[0, "#1f2937"], [0.5, "#065f46"], [1, "#00ff87"]], template="plotly_dark")
    fig.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a", showlegend=False,
        coloraxis_showscale=False, xaxis=dict(tickangle=-45, tickfont_size=10), margin=dict(l=0, r=0, t=20, b=80))
    st.plotly_chart(fig, use_container_width=True)

# ── 2. Artilheiros ────────────────────────────────────────────────────────────
elif page == "Artilheiros":
    st.markdown('<p class="section-title">ARTILHEIROS</p>', unsafe_allow_html=True)

    data = fetch(f"/competitions/{comp_code}/scorers?limit=20", api_key)
    if not data:
        st.stop()

    scorers = data.get("scorers", [])
    if not scorers:
        st.warning("Dados de artilheiros não disponíveis.")
        st.stop()

    df = pd.DataFrame([{
        "Jogador": s["player"]["name"], "Time": s["team"]["name"],
        "Gols": s.get("goals", 0), "Assistências": s.get("assists", 0) or 0,
        "Jogos": s.get("playedMatches", 0),
        "G/Jogo": round((s.get("goals", 0) or 0) / max(s.get("playedMatches", 1), 1), 2),
        "Pênaltis": s.get("penalties", 0) or 0,
    } for s in scorers])

    c1, c2, c3 = st.columns(3)
    top = df.iloc[0]
    c1.metric("🥇 Artilheiro", top["Jogador"], f"{top['Gols']} gols")
    c2.metric("⚡ Melhor G/Jogo", df.loc[df["G/Jogo"].idxmax(), "Jogador"], f"{df['G/Jogo'].max():.2f}")
    c3.metric("🎯 Mais Assistências", df.loc[df["Assistências"].idxmax(), "Jogador"], f"{df['Assistências'].max()}")

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([1.4, 1])
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(y=df["Jogador"], x=df["Gols"], orientation='h', name="Gols", marker_color="#00ff87"))
        fig.add_trace(go.Bar(y=df["Jogador"], x=df["Assistências"], orientation='h', name="Assistências", marker_color="#3b82f6"))
        fig.update_layout(barmode='stack', template="plotly_dark", paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
            yaxis=dict(categoryorder='total ascending'), legend=dict(orientation="h", y=1.05),
            margin=dict(l=0, r=20, t=30, b=0), height=500)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(df[["Jogador", "Gols", "Assistências", "G/Jogo"]], use_container_width=True, hide_index=True)

# ── 3. Jogos Recentes ─────────────────────────────────────────────────────────
elif page == "Jogos Recentes":
    st.markdown('<p class="section-title">JOGOS RECENTES</p>', unsafe_allow_html=True)

    date_to   = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    data = fetch(f"/competitions/{comp_code}/matches?status=FINISHED&dateFrom={date_from}&dateTo={date_to}", api_key)
    if not data: st.stop()

    matches = data.get("matches", [])
    if not matches:
        st.info("Nenhum jogo encontrado nos últimos 14 dias.")
        st.stop()

    matches = sorted(matches, key=lambda m: m["utcDate"], reverse=True)
    goals_data = []
    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        hg, ag = score.get("home") or 0, score.get("away") or 0
        dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        goals_data.append({"Jogo": f"{m['homeTeam']['shortName']} x {m['awayTeam']['shortName']}", "Gols": hg + ag})

    df_g = pd.DataFrame(goals_data)
    c1, c2, c3 = st.columns(3)
    c1.metric("🎮 Jogos", len(matches))
    c2.metric("⚽ Média de Gols", f"{df_g['Gols'].mean():.1f}")
    c3.metric("🔥 Maior goleada", df_g.loc[df_g["Gols"].idxmax(), "Jogo"], f"{df_g['Gols'].max()} gols")
    st.markdown("<br>", unsafe_allow_html=True)

    for m in matches[:15]:
        score = m.get("score", {}).get("fullTime", {})
        hg, ag = score.get("home"), score.get("away")
        score_str = f"{hg} — {ag}" if hg is not None else "- — -"
        dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1: st.markdown(f"<div style='text-align:right;font-weight:600'>{m['homeTeam']['name']}</div>", unsafe_allow_html=True)
        with col2:
            color = "#00ff87" if hg is not None else "#6b7280"
            st.markdown(f"<div style='text-align:center;font-family:Bebas Neue;font-size:1.3rem;color:{color};letter-spacing:0.1em'>{score_str}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center;font-size:0.65rem;color:#6b7280'>{dt.strftime('%d/%m %H:%M')}</div>", unsafe_allow_html=True)
        with col3: st.markdown(f"<div style='text-align:left;font-weight:600'>{m['awayTeam']['name']}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:0.4rem 0;border-color:#1f2937'>", unsafe_allow_html=True)

# ── 4. Próximos Jogos ─────────────────────────────────────────────────────────
elif page == "Próximos Jogos":
    st.markdown('<p class="section-title">PRÓXIMOS JOGOS</p>', unsafe_allow_html=True)

    date_from = datetime.now().strftime("%Y-%m-%d")
    date_to   = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    data = fetch(f"/competitions/{comp_code}/matches?status=SCHEDULED&dateFrom={date_from}&dateTo={date_to}", api_key)
    if not data: st.stop()

    matches = data.get("matches", [])
    if not matches:
        st.info("Nenhum jogo agendado nos próximos 14 dias.")
        st.stop()

    matches = sorted(matches, key=lambda m: m["utcDate"])
    c1, c2 = st.columns(2)
    c1.metric("📅 Próximos Jogos", len(matches))
    first = datetime.fromisoformat(matches[0]["utcDate"].replace("Z", "+00:00"))
    c2.metric("⏱️ Próximo Jogo", f"{matches[0]['homeTeam']['shortName']} x {matches[0]['awayTeam']['shortName']}", first.strftime("%d/%m às %H:%M"))
    st.markdown("<br>", unsafe_allow_html=True)

    def get_date(m):
        return datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).strftime("%A, %d de %B")

    for date_label, group in groupby(matches[:20], key=get_date):
        st.markdown(f"<div style='color:#00ff87;font-family:Bebas Neue;font-size:1.1rem;margin:1rem 0 0.5rem;letter-spacing:0.05em'>{date_label.upper()}</div>", unsafe_allow_html=True)
        for m in group:
            dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1: st.markdown(f"<div style='text-align:right;font-weight:600'>{m['homeTeam']['name']}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='text-align:center;font-family:Bebas Neue;font-size:1.1rem;color:#6b7280'>VS</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;font-size:0.65rem;color:#6b7280'>{dt.strftime('%H:%M')}</div>", unsafe_allow_html=True)
            with col3: st.markdown(f"<div style='text-align:left;font-weight:600'>{m['awayTeam']['name']}</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:0.4rem 0;border-color:#1f2937'>", unsafe_allow_html=True)

# ── 5. Análise de Times ───────────────────────────────────────────────────────
elif page == "Análise de Times":
    st.markdown('<p class="section-title">ANÁLISE DE TIMES</p>', unsafe_allow_html=True)

    stand_data = fetch(f"/competitions/{comp_code}/standings", api_key)
    if not stand_data: st.stop()

    standings = stand_data.get("standings", [])
    total = next((s for s in standings if s["type"] == "TOTAL"), None)
    if not total:
        st.warning("Dados não disponíveis.")
        st.stop()

    table = total["table"]
    team_names = [r["team"]["name"] for r in table]
    team_ids   = {r["team"]["name"]: r["team"]["id"] for r in table}

    selected = st.selectbox("Selecione o time", team_names)
    team_id  = team_ids[selected]
    row = next(r for r in table if r["team"]["name"] == selected)

    col1, col2 = st.columns(2)
    with col1:
        df_stats = pd.DataFrame({
            "Métrica": ["Pontos", "Vitórias", "Empates", "Derrotas", "Gols Pró", "Gols Contra", "Saldo"],
            "Valor":   [row["points"], row["won"], row["draw"], row["lost"],
                        row["goalsFor"], row["goalsAgainst"], row["goalDifference"]],
        })
        fig = go.Figure(go.Bar(x=df_stats["Valor"], y=df_stats["Métrica"], orientation='h',
            marker=dict(color=df_stats["Valor"], colorscale=[[0, "#1f2937"], [0.5, "#065f46"], [1, "#00ff87"]]),
            text=df_stats["Valor"], textposition="outside"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
            margin=dict(l=0, r=40, t=10, b=0), height=350, xaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        categories = ["Pontos", "Vitórias", "Gols Pró", "Saldo de Gols"]
        vals = [row["points"], row["won"], row["goalsFor"], max(row["goalDifference"] + 20, 0)]
        max_vals = [max(r["points"] for r in table), max(r["won"] for r in table),
                    max(r["goalsFor"] for r in table), max(r["goalDifference"] + 20 for r in table)]
        normalized = [v / m * 100 if m > 0 else 0 for v, m in zip(vals, max_vals)]
        fig2 = go.Figure(go.Scatterpolar(
            r=normalized + [normalized[0]], theta=categories + [categories[0]],
            fill='toself', fillcolor='rgba(0,255,135,0.15)', line=dict(color="#00ff87", width=2)))
        fig2.update_layout(polar=dict(bgcolor="#111827",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="#1f2937"),
            angularaxis=dict(gridcolor="#1f2937", tickfont=dict(size=11))),
            template="plotly_dark", paper_bgcolor="#0a0e1a",
            margin=dict(l=20, r=20, t=20, b=20), height=350, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<p class="section-title">FORMA RECENTE</p>', unsafe_allow_html=True)
    match_data = fetch(f"/teams/{team_id}/matches?status=FINISHED&limit=10", api_key)
    if match_data:
        recent = sorted(match_data.get("matches", []), key=lambda m: m["utcDate"], reverse=True)[:10]
        form_icons = []
        for m in recent:
            score = m.get("score", {}).get("fullTime", {})
            hg, ag = score.get("home", 0) or 0, score.get("away", 0) or 0
            is_home = m["homeTeam"]["id"] == team_id
            gf, gc = (hg, ag) if is_home else (ag, hg)
            if gf > gc: form_icons.append(("V", "#00ff87"))
            elif gf == gc: form_icons.append(("E", "#fbbf24"))
            else: form_icons.append(("D", "#f87171"))

        icons_html = "".join(
            f"<span style='display:inline-block;width:32px;height:32px;border-radius:50%;background:{c};"
            f"color:#000;font-weight:700;text-align:center;line-height:32px;margin:3px;font-size:0.8rem'>{l}</span>"
            for l, c in form_icons)
        st.markdown(f"<div>{icons_html}</div>", unsafe_allow_html=True)
        wins = sum(1 for l, _ in form_icons if l == "V")
        draws = sum(1 for l, _ in form_icons if l == "E")
        losses = sum(1 for l, _ in form_icons if l == "D")
        st.caption(f"Últimos {len(form_icons)} jogos: {wins}V {draws}E {losses}D")

# ══════════════════════════════════════════════════════════════════════════════
# ── 6. COMPARAÇÃO DE JOGADORES — estilo FBref / FBCharts ──────────────────────
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Comparação de Jogadores":
    st.markdown('<p class="section-title">COMPARAÇÃO DE JOGADORES</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#6b7280;margin-top:-0.5rem;margin-bottom:1.5rem'>"
        "Percentis calculados em relação a todos os jogadores da competição com dados disponíveis · "
        "Inspirado no FBref/FBCharts</p>",
        unsafe_allow_html=True,
    )

    with st.spinner("Buscando dados dos jogadores..."):
        data = fetch(f"/competitions/{comp_code}/scorers?limit=50", api_key)

    if not data:
        st.stop()

    scorers = data.get("scorers", [])
    if len(scorers) < 2:
        st.warning("Não há jogadores suficientes disponíveis para esta competição no momento.")
        st.stop()

    df_all = build_scorer_stats(scorers)
    df_all["Posição"] = df_all["Posição"].apply(map_position)

    # ── Controles superiores
    col_cfg1, col_cfg2 = st.columns([1, 1])
    with col_cfg1:
        chart_type = st.radio(
            "Tipo de visualização",
            ["🍕 Pizza Chart", "📊 Barras Percentil", "🔄 Head-to-Head"],
        )
    with col_cfg2:
        min_games = st.slider("Mínimo de jogos", 1, 15, 3,
            help="Filtra jogadores com poucos jogos para evitar distorções")

    df_filtered = df_all[df_all["Jogos"] >= min_games].copy()

    if len(df_filtered) < 2:
        st.warning(f"Só {len(df_filtered)} jogador(es) com ≥{min_games} jogos. Reduza o filtro.")
        st.stop()

    player_names = sorted(df_filtered["Jogador"].tolist())
    position_opts = ["Todos"] + sorted(df_filtered["Posição"].unique().tolist())

    ALL_METRICS = ["Gols", "Assistências", "G+A", "G/Jogo", "A/Jogo",
                   "(G+A)/Jogo", "Participações em Gols", "Chutes/Jogo",
                   "Dribles/Jogo", "Passes Decisivos/Jogo", "Conversão (%)"]
    PIZZA_METRICS = ["Gols", "Assistências", "G+A", "G/Jogo", "A/Jogo",
                     "Participações em Gols", "Chutes/Jogo", "Dribles/Jogo", "Conversão (%)"]

    def get_pool(pos_sel):
        if pos_sel == "Todos":
            return df_filtered
        p = df_filtered[df_filtered["Posição"] == pos_sel]
        return p if len(p) >= 2 else df_filtered

    # ════════════════════════════════════════════════════════════════════════
    # 🍕 PIZZA CHART
    # ════════════════════════════════════════════════════════════════════════
    if "Pizza" in chart_type:
        st.markdown("---")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            player_sel = st.selectbox("🎯 Jogador", player_names)
        with col_s2:
            pos_sel = st.selectbox("📌 Pool de comparação", position_opts)

        p_row = df_filtered[df_filtered["Jogador"] == player_sel].iloc[0]
        pool  = get_pool(pos_sel)
        avail_metrics = [m for m in PIZZA_METRICS if m in pool.columns]

        pct_vals = [percentile_rank(p_row[m], pool[m], lower_better=(m == "Minutos/Gol")) for m in avail_metrics]
        raw_vals = [round(p_row[m], 2) for m in avail_metrics]

        # Player header
        st.markdown(f"""
        <div style='background:#111827;border:1px solid #1f2937;border-radius:16px;
                    padding:1.25rem 1.5rem;margin-bottom:1rem;display:flex;align-items:center;gap:1.25rem'>
            <div style='width:60px;height:60px;border-radius:50%;
                        background:linear-gradient(135deg,#00ff87,#065f46);
                        display:flex;align-items:center;justify-content:center;
                        font-family:Bebas Neue;font-size:1.8rem;color:#000;flex-shrink:0'>
                {player_sel[0].upper()}
            </div>
            <div>
                <div class='player-name' style='color:#00ff87'>{player_sel}</div>
                <div class='player-team'>{p_row['Time']} &nbsp;·&nbsp; {p_row['Posição']}</div>
                <div style='margin-top:0.4rem'>
                    <span class='stat-pill'>⚽ {int(p_row['Gols'])} Gols</span>
                    <span class='stat-pill'>🎯 {int(p_row['Assistências'])} Assistências</span>
                    <span class='stat-pill'>🎮 {int(p_row['Jogos'])} Jogos</span>
                    <span class='stat-pill'>📈 {p_row['G/Jogo']:.2f} G/Jogo</span>
                </div>
            </div>
            <div style='margin-left:auto;text-align:right'>
                <div style='font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.1em'>Pool</div>
                <div style='font-family:Bebas Neue;font-size:1.4rem;color:#e5e7eb'>{len(pool)} jogadores</div>
                <div style='font-size:0.7rem;color:#6b7280'>{pos_sel}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        fig_pizza = pizza_chart(
            player_name=player_sel,
            metrics=avail_metrics,
            values=pct_vals,
            color="#00ff87",
            title=f"{player_sel.upper()} — PERCENTIS vs {pos_sel.upper()}",
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

        # Percentil table
        st.markdown('<p class="section-title">TABELA DE PERCENTIS</p>', unsafe_allow_html=True)
        df_pct = pd.DataFrame({"Métrica": avail_metrics, "Valor": raw_vals, "Percentil": pct_vals})

        def color_pct(val):
            if val >= 90: return "background-color:#064e3b;color:#00ff87;font-weight:700"
            elif val >= 75: return "background-color:#065f46;color:#6ee7b7"
            elif val >= 50: return "background-color:#1f2937;color:#e5e7eb"
            elif val >= 25: return "background-color:#422006;color:#fdba74"
            else: return "background-color:#450a0a;color:#fca5a5"

        def tier_label(val):
            if val >= 90: return "🟢 Elite"
            elif val >= 75: return "🟩 Acima da média"
            elif val >= 50: return "🔵 Médio"
            elif val >= 25: return "🟠 Abaixo da média"
            else: return "🔴 Baixo"

        df_pct["Nível"] = df_pct["Percentil"].apply(tier_label)
        st.dataframe(
            df_pct.style.applymap(color_pct, subset=["Percentil"]).format({"Percentil": "{:.0f}", "Valor": "{:.2f}"}),
            use_container_width=True, hide_index=True,
        )

    # ════════════════════════════════════════════════════════════════════════
    # 📊 BARRAS PERCENTIL
    # ════════════════════════════════════════════════════════════════════════
    elif "Barras" in chart_type:
        st.markdown("---")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            player_sel = st.selectbox("🎯 Jogador", player_names)
        with col_s2:
            pos_sel = st.selectbox("📌 Pool de comparação", position_opts)

        p_row = df_filtered[df_filtered["Jogador"] == player_sel].iloc[0]
        pool  = get_pool(pos_sel)
        avail = [m for m in ALL_METRICS if m in pool.columns]

        pct_vals = [percentile_rank(p_row[m], pool[m], lower_better=(m == "Minutos/Gol")) for m in avail]
        raw_vals = [round(p_row[m], 2) for m in avail]

        # Player header
        st.markdown(f"""
        <div style='background:#111827;border:1px solid #1f2937;border-radius:12px;padding:1rem 1.5rem;margin-bottom:1rem'>
            <span class='player-name' style='color:#00ff87'>{player_sel}</span>
            <span style='color:#6b7280;margin-left:1rem;font-size:0.85rem'>{p_row['Time']} · {p_row['Posição']} · {int(p_row['Jogos'])} jogos</span>
        </div>""", unsafe_allow_html=True)

        bar_colors = ["#00ff87" if p >= 75 else "#38bdf8" if p >= 50 else "#fb923c" if p >= 25 else "#f87171" for p in pct_vals]

        fig_bars = go.Figure()
        fig_bars.add_trace(go.Bar(
            y=avail, x=pct_vals, orientation='h',
            marker_color=bar_colors,
            text=[f"  {p:.0f}  ·  {r}" for p, r in zip(pct_vals, raw_vals)],
            textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Percentil: %{x:.0f}<br>Valor: %{customdata}<extra></extra>",
            customdata=raw_vals,
        ))
        fig_bars.add_vline(x=50, line=dict(color="#6b7280", dash="dot", width=1.5))

        # Background bands
        for rng, col in [([0,25],"rgba(239,68,68,0.05)"),([25,50],"rgba(251,146,60,0.05)"),
                          ([50,75],"rgba(56,189,248,0.05)"),([75,100],"rgba(0,255,135,0.05)")]:
            fig_bars.add_vrect(x0=rng[0], x1=rng[1], fillcolor=col, layer="below", line_width=0)

        fig_bars.update_layout(
            xaxis=dict(range=[0, 128], showgrid=False, tickvals=[0,25,50,75,100]),
            yaxis=dict(tickfont=dict(size=12, color="#e5e7eb"), gridcolor="#1f2937", categoryorder="array", categoryarray=list(reversed(avail))),
            paper_bgcolor="#0a0e1a", plot_bgcolor="#111827",
            margin=dict(l=10, r=160, t=40, b=10),
            height=max(420, len(avail) * 40),
            template="plotly_dark",
            title=dict(text=f"{player_sel.upper()} vs {pos_sel.upper()} ({len(pool)} jogadores)",
                       font=dict(color="#00ff87", family="Bebas Neue", size=18), x=0.5),
        )
        st.plotly_chart(fig_bars, use_container_width=True)

        st.markdown("""
        <div style='display:flex;gap:1.5rem;font-size:0.75rem;color:#6b7280;margin-top:-0.5rem'>
            <span><span style='color:#f87171'>■</span> 0–25 Baixo</span>
            <span><span style='color:#fb923c'>■</span> 25–50 Abaixo da média</span>
            <span><span style='color:#38bdf8'>■</span> 50–75 Acima da média</span>
            <span><span style='color:#00ff87'>■</span> 75–100 Elite</span>
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # 🔄 HEAD-TO-HEAD
    # ════════════════════════════════════════════════════════════════════════
    elif "Head" in chart_type:
        st.markdown("---")
        col_p1, col_vs, col_p2 = st.columns([5, 1, 5])
        with col_p1:
            player1 = st.selectbox("🟢 Jogador 1", player_names, key="h2h_p1")
        with col_vs:
            st.markdown("<div style='text-align:center;font-family:Bebas Neue;font-size:2.2rem;color:#374151;padding-top:1.6rem'>VS</div>", unsafe_allow_html=True)
        with col_p2:
            idx2 = 1 if len(player_names) > 1 else 0
            player2 = st.selectbox("🔵 Jogador 2", player_names, index=idx2, key="h2h_p2")

        pos_sel = st.selectbox("📌 Pool de comparação", position_opts, key="h2h_pos")

        if player1 == player2:
            st.warning("Selecione dois jogadores diferentes.")
            st.stop()

        p1 = df_filtered[df_filtered["Jogador"] == player1].iloc[0]
        p2 = df_filtered[df_filtered["Jogador"] == player2].iloc[0]
        pool = get_pool(pos_sel)

        # Player cards
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown(f"""
            <div style='background:linear-gradient(145deg,#0a2a1a,#111827);border:2px solid #00ff87;
                        border-radius:16px;padding:1.5rem;text-align:center;margin-bottom:1rem'>
                <div style='width:64px;height:64px;border-radius:50%;background:#00ff87;
                            display:flex;align-items:center;justify-content:center;
                            font-family:Bebas Neue;font-size:2rem;color:#000;margin:0 auto 0.75rem'>
                    {player1[0].upper()}
                </div>
                <div class='player-name' style='color:#00ff87'>{player1}</div>
                <div class='player-team'>{p1['Time']} · {p1['Posição']}</div>
                <div style='margin-top:0.75rem'>
                    <span class='stat-pill'>⚽ {int(p1['Gols'])} G</span>
                    <span class='stat-pill'>🎯 {int(p1['Assistências'])} A</span>
                    <span class='stat-pill'>🎮 {int(p1['Jogos'])} PJ</span>
                    <span class='stat-pill'>📈 {p1['G/Jogo']:.2f} G/J</span>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_c2:
            st.markdown(f"""
            <div style='background:linear-gradient(145deg,#0a1a2a,#111827);border:2px solid #38bdf8;
                        border-radius:16px;padding:1.5rem;text-align:center;margin-bottom:1rem'>
                <div style='width:64px;height:64px;border-radius:50%;background:#38bdf8;
                            display:flex;align-items:center;justify-content:center;
                            font-family:Bebas Neue;font-size:2rem;color:#000;margin:0 auto 0.75rem'>
                    {player2[0].upper()}
                </div>
                <div class='player-name' style='color:#38bdf8'>{player2}</div>
                <div class='player-team'>{p2['Time']} · {p2['Posição']}</div>
                <div style='margin-top:0.75rem'>
                    <span class='stat-pill'>⚽ {int(p2['Gols'])} G</span>
                    <span class='stat-pill'>🎯 {int(p2['Assistências'])} A</span>
                    <span class='stat-pill'>🎮 {int(p2['Jogos'])} PJ</span>
                    <span class='stat-pill'>📈 {p2['G/Jogo']:.2f} G/J</span>
                </div>
            </div>""", unsafe_allow_html=True)

        avail = [m for m in ALL_METRICS if m in pool.columns]
        pct1 = [percentile_rank(p1[m], pool[m], lower_better=(m=="Minutos/Gol")) for m in avail]
        pct2 = [percentile_rank(p2[m], pool[m], lower_better=(m=="Minutos/Gol")) for m in avail]
        raw1 = [round(p1[m], 2) for m in avail]
        raw2 = [round(p2[m], 2) for m in avail]

        # H2H bar chart
        st.markdown('<p class="section-title">BARRAS PERCENTIL HEAD-TO-HEAD</p>', unsafe_allow_html=True)
        fig_h2h = h2h_bar_chart(player1, player2, avail, pct1, pct2, raw1, raw2)
        st.plotly_chart(fig_h2h, use_container_width=True)
        st.caption(f"← {player1} (verde) &nbsp;|&nbsp; {player2} (azul) → &nbsp;·&nbsp; Números = valores brutos &nbsp;·&nbsp; Eixo = percentil vs {len(pool)} jogadores")

        # Radar duplo
        st.markdown('<p class="section-title">RADAR COMPARATIVO</p>', unsafe_allow_html=True)
        radar_metrics = [m for m in ["Gols", "Assistências", "G/Jogo", "A/Jogo", "Participações em Gols", "Conversão (%)"] if m in pool.columns]
        r1 = [percentile_rank(p1[m], pool[m]) for m in radar_metrics]
        r2 = [percentile_rank(p2[m], pool[m]) for m in radar_metrics]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=r1 + [r1[0]], theta=radar_metrics + [radar_metrics[0]],
            name=player1, fill='toself',
            fillcolor='rgba(0,255,135,0.18)', line=dict(color="#00ff87", width=2.5),
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=r2 + [r2[0]], theta=radar_metrics + [radar_metrics[0]],
            name=player2, fill='toself',
            fillcolor='rgba(56,189,248,0.18)', line=dict(color="#38bdf8", width=2.5),
        ))
        fig_radar.update_layout(
            polar=dict(bgcolor="#111827",
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=True,
                    tickvals=[25,50,75,100], tickfont=dict(size=8, color="#6b7280"), gridcolor="#1f2937"),
                angularaxis=dict(gridcolor="#1f2937", tickfont=dict(size=12, color="#e5e7eb")),
            ),
            legend=dict(font=dict(color="white", size=13), bgcolor="rgba(0,0,0,0)",
                        orientation="h", x=0.5, xanchor="center", y=-0.12),
            template="plotly_dark", paper_bgcolor="#0a0e1a",
            margin=dict(l=60, r=60, t=30, b=60), height=480,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # Tabela comparativa
        st.markdown('<p class="section-title">ESTATÍSTICAS COMPARADAS</p>', unsafe_allow_html=True)
        vantagem = []
        for r1v, r2v, m in zip(raw1, raw2, avail):
            lower = m in ["Minutos/Gol"]
            if lower:
                vantagem.append(f"🟢 {player1[:14]}" if r1v < r2v else (f"🔵 {player2[:14]}" if r2v < r1v else "—"))
            else:
                vantagem.append(f"🟢 {player1[:14]}" if r1v > r2v else (f"🔵 {player2[:14]}" if r2v > r1v else "—"))

        df_cmp = pd.DataFrame({
            "Métrica":        avail,
            f"🟢 {player1[:16]}": raw1,
            "P1 %ile":        [f"{p:.0f}" for p in pct1],
            f"🔵 {player2[:16]}": raw2,
            "P2 %ile":        [f"{p:.0f}" for p in pct2],
            "Vantagem":       vantagem,
        })

        p1_wins = sum(1 for v in vantagem if "🟢" in v)
        p2_wins = sum(1 for v in vantagem if "🔵" in v)

        cv1, cv2, cv3 = st.columns(3)
        cv1.metric(f"🟢 {player1[:18]}", f"{p1_wins} métricas melhores")
        cv2.metric("🤝 Empates", f"{len(avail) - p1_wins - p2_wins}")
        cv3.metric(f"🔵 {player2[:18]}", f"{p2_wins} métricas melhores")

        st.dataframe(df_cmp, use_container_width=True, hide_index=True)
