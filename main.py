
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

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

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: var(--muted) !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
}
[data-testid="metric-container"] label { color: var(--muted) !important; font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.1em; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--green) !important; font-family: 'Bebas Neue', sans-serif; font-size: 2rem !important; }

/* Buttons */
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

/* Selectbox */
.stSelectbox > div > div {
    background: var(--card) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}

/* Tables */
.stDataFrame { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }

/* Dividers */
hr { border-color: var(--border) !important; }

/* Headers */
.section-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    color: var(--green);
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
    border-left: 4px solid var(--green);
    padding-left: 0.75rem;
}
.badge {
    display: inline-block;
    background: #1f2937;
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0.2rem 0.75rem;
    font-size: 0.75rem;
    color: var(--muted);
    margin-right: 0.5rem;
}
.match-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin-bottom: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

# ─── API Helper ───────────────────────────────────────────────────────────────
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
        ["Classificação", "Artilheiros", "Jogos Recentes", "Próximos Jogos", "Análise de Times"],
    )

    st.markdown("---")
    st.markdown("<span style='color:#6b7280;font-size:0.7rem'>Dados via football-data.org</span>", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"<h1 style='font-size:3rem;margin-bottom:0'>{comp_name}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#6b7280;margin-top:0'>Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>", unsafe_allow_html=True)
st.markdown("---")

# ─── Pages ────────────────────────────────────────────────────────────────────

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
        "Pos":       r["position"],
        "Time":      r["team"]["name"],
        "PJ":        r["playedGames"],
        "V":         r["won"],
        "E":         r["draw"],
        "D":         r["lost"],
        "GP":        r["goalsFor"],
        "GC":        r["goalsAgainst"],
        "SG":        r["goalDifference"],
        "Pts":       r["points"],
    } for r in table])

    # Highlight
    def highlight_row(row):
        pos = row["Pos"]
        if pos <= 4:
            return ["background-color:#0a2a1a; color:#00ff87"] * len(row)
        elif pos <= 6:
            return ["background-color:#1a1a0a; color:#fbbf24"] * len(row)
        elif pos > len(df) - 3:
            return ["background-color:#2a0a0a; color:#f87171"] * len(row)
        return [""] * len(row)

    c1, c2, c3, c4 = st.columns(4)
    leader = df.iloc[0]
    c1.metric("🥇 Líder", leader["Time"], f"{leader['Pts']} pts")
    c2.metric("⚽ Mais gols", df.loc[df["GP"].idxmax(), "Time"], f"{df['GP'].max()} gols")
    c3.metric("🛡️ Menos gols sofridos", df.loc[df["GC"].idxmin(), "Time"], f"{df['GC'].min()} GC")
    c4.metric("📊 Times", len(df))

    st.markdown("<br>", unsafe_allow_html=True)
    st.dataframe(
        df.style.apply(highlight_row, axis=1).format({"SG": "{:+d}"}),
        use_container_width=True,
        hide_index=True,
    )

    # Chart
    st.markdown('<p class="section-title">PONTOS POR TIME</p>', unsafe_allow_html=True)
    fig = px.bar(
        df, x="Time", y="Pts", color="Pts",
        color_continuous_scale=[[0, "#1f2937"], [0.5, "#065f46"], [1, "#00ff87"]],
        template="plotly_dark",
    )
    fig.update_layout(
        paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
        showlegend=False, coloraxis_showscale=False,
        xaxis=dict(tickangle=-45, tickfont_size=10),
        margin=dict(l=0, r=0, t=20, b=80),
    )
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
        "Jogador":     s["player"]["name"],
        "Time":        s["team"]["name"],
        "Gols":        s.get("goals", 0),
        "Assistências": s.get("assists", 0) or 0,
        "Jogos":       s.get("playedMatches", 0),
        "G/Jogo":      round((s.get("goals", 0) or 0) / max(s.get("playedMatches", 1), 1), 2),
        "Pênaltis":    s.get("penalties", 0) or 0,
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
        fig.add_trace(go.Bar(
            y=df["Jogador"], x=df["Gols"],
            orientation='h', name="Gols",
            marker_color="#00ff87",
        ))
        fig.add_trace(go.Bar(
            y=df["Jogador"], x=df["Assistências"],
            orientation='h', name="Assistências",
            marker_color="#3b82f6",
        ))
        fig.update_layout(
            barmode='stack', template="plotly_dark",
            paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
            yaxis=dict(categoryorder='total ascending'),
            legend=dict(orientation="h", y=1.05),
            margin=dict(l=0, r=20, t=30, b=0), height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(df[["Jogador", "Gols", "Assistências", "G/Jogo"]], use_container_width=True, hide_index=True)

# ── 3. Jogos Recentes ─────────────────────────────────────────────────────────
elif page == "Jogos Recentes":
    st.markdown('<p class="section-title">JOGOS RECENTES</p>', unsafe_allow_html=True)

    date_to   = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    data = fetch(f"/competitions/{comp_code}/matches?status=FINISHED&dateFrom={date_from}&dateTo={date_to}", api_key)
    if not data:
        st.stop()

    matches = data.get("matches", [])
    if not matches:
        st.info("Nenhum jogo encontrado nos últimos 14 dias.")
        st.stop()

    matches = sorted(matches, key=lambda m: m["utcDate"], reverse=True)

    # Goals per match chart
    goals_data = []
    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        home_g = score.get("home") or 0
        away_g = score.get("away") or 0
        dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        goals_data.append({
            "Jogo": f"{m['homeTeam']['shortName']} x {m['awayTeam']['shortName']}",
            "Gols": home_g + away_g,
            "Data": dt.strftime("%d/%m"),
        })

    df_g = pd.DataFrame(goals_data)
    avg = df_g["Gols"].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("🎮 Jogos", len(matches))
    c2.metric("⚽ Média de Gols", f"{avg:.1f}")
    c3.metric("🔥 Jogo mais goleada", df_g.loc[df_g["Gols"].idxmax(), "Jogo"], f"{df_g['Gols'].max()} gols")

    st.markdown("<br>", unsafe_allow_html=True)

    for m in matches[:15]:
        score  = m.get("score", {}).get("fullTime", {})
        hg     = score.get("home")
        ag     = score.get("away")
        score_str = f"{hg} — {ag}" if hg is not None else "- — -"
        dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        date_str = dt.strftime("%d/%m %H:%M")

        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.markdown(f"<div style='text-align:right;font-weight:600'>{m['homeTeam']['name']}</div>", unsafe_allow_html=True)
        with col2:
            color = "#00ff87" if hg is not None else "#6b7280"
            st.markdown(f"<div style='text-align:center;font-family:Bebas Neue;font-size:1.3rem;color:{color};letter-spacing:0.1em'>{score_str}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center;font-size:0.65rem;color:#6b7280'>{date_str}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='text-align:left;font-weight:600'>{m['awayTeam']['name']}</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin:0.4rem 0;border-color:#1f2937'>", unsafe_allow_html=True)

# ── 4. Próximos Jogos ─────────────────────────────────────────────────────────
elif page == "Próximos Jogos":
    st.markdown('<p class="section-title">PRÓXIMOS JOGOS</p>', unsafe_allow_html=True)

    date_from = datetime.now().strftime("%Y-%m-%d")
    date_to   = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    data = fetch(f"/competitions/{comp_code}/matches?status=SCHEDULED&dateFrom={date_from}&dateTo={date_to}", api_key)
    if not data:
        st.stop()

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

    # Group by date
    from itertools import groupby
    def get_date(m):
        return datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).strftime("%A, %d de %B")

    for date_label, group in groupby(matches[:20], key=get_date):
        st.markdown(f"<div style='color:#00ff87;font-family:Bebas Neue;font-size:1.1rem;margin:1rem 0 0.5rem;letter-spacing:0.05em'>{date_label.upper()}</div>", unsafe_allow_html=True)
        for m in group:
            dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1:
                st.markdown(f"<div style='text-align:right;font-weight:600'>{m['homeTeam']['name']}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='text-align:center;font-family:Bebas Neue;font-size:1.1rem;color:#6b7280'>VS</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;font-size:0.65rem;color:#6b7280'>{dt.strftime('%H:%M')}</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div style='text-align:left;font-weight:600'>{m['awayTeam']['name']}</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:0.4rem 0;border-color:#1f2937'>", unsafe_allow_html=True)

# ── 5. Análise de Times ───────────────────────────────────────────────────────
elif page == "Análise de Times":
    st.markdown('<p class="section-title">ANÁLISE DE TIMES</p>', unsafe_allow_html=True)

    stand_data = fetch(f"/competitions/{comp_code}/standings", api_key)
    if not stand_data:
        st.stop()

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

    col1, col2 = st.columns(2)

    with col1:
        row = next(r for r in table if r["team"]["name"] == selected)
        df_stats = pd.DataFrame({
            "Métrica": ["Pontos", "Vitórias", "Empates", "Derrotas", "Gols Pró", "Gols Contra", "Saldo"],
            "Valor":   [row["points"], row["won"], row["draw"], row["lost"],
                        row["goalsFor"], row["goalsAgainst"], row["goalDifference"]],
        })

        fig = go.Figure(go.Bar(
            x=df_stats["Valor"], y=df_stats["Métrica"],
            orientation='h',
            marker=dict(
                color=df_stats["Valor"],
                colorscale=[[0, "#1f2937"], [0.5, "#065f46"], [1, "#00ff87"]],
            ),
            text=df_stats["Valor"], textposition="outside",
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
            margin=dict(l=0, r=40, t=10, b=0), height=350,
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Radar chart
        categories = ["Pontos", "Vitórias", "Gols Pró", "Saldo de Gols"]
        vals = [row["points"], row["won"], row["goalsFor"], max(row["goalDifference"] + 20, 0)]
        max_vals = [
            max(r["points"] for r in table),
            max(r["won"] for r in table),
            max(r["goalsFor"] for r in table),
            max(r["goalDifference"] + 20 for r in table),
        ]
        normalized = [v / m * 100 if m > 0 else 0 for v, m in zip(vals, max_vals)]

        fig2 = go.Figure(go.Scatterpolar(
            r=normalized + [normalized[0]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(0,255,135,0.15)',
            line=dict(color="#00ff87", width=2),
        ))
        fig2.update_layout(
            polar=dict(
                bgcolor="#111827",
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="#1f2937"),
                angularaxis=dict(gridcolor="#1f2937", tickfont=dict(size=11)),
            ),
            template="plotly_dark",
            paper_bgcolor="#0a0e1a",
            margin=dict(l=20, r=20, t=20, b=20), height=350,
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Recent form
    st.markdown('<p class="section-title">FORMA RECENTE</p>', unsafe_allow_html=True)
    match_data = fetch(f"/teams/{team_id}/matches?status=FINISHED&limit=10", api_key)
    if match_data:
        recent = sorted(match_data.get("matches", []), key=lambda m: m["utcDate"], reverse=True)[:10]
        form_icons = []
        for m in recent:
            score = m.get("score", {}).get("fullTime", {})
            hg, ag = score.get("home", 0) or 0, score.get("away", 0) or 0
            is_home = m["homeTeam"]["id"] == team_id
            gf = hg if is_home else ag
            gc = ag if is_home else hg
            if gf > gc:
                form_icons.append(("V", "#00ff87"))
            elif gf == gc:
                form_icons.append(("E", "#fbbf24"))
            else:
                form_icons.append(("D", "#f87171"))

        icons_html = "".join(
            f"<span style='display:inline-block;width:32px;height:32px;border-radius:50%;background:{c};"
            f"color:#000;font-weight:700;text-align:center;line-height:32px;margin:3px;font-size:0.8rem'>{l}</span>"
            for l, c in form_icons
        )
        st.markdown(f"<div>{icons_html}</div>", unsafe_allow_html=True)
        wins   = sum(1 for l, _ in form_icons if l == "V")
        draws  = sum(1 for l, _ in form_icons if l == "E")
        losses = sum(1 for l, _ in form_icons if l == "D")
        st.caption(f"Últimos {len(form_icons)} jogos: {wins}V {draws}E {losses}D")
