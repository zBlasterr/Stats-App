"""
⚽ Football Stats — Streamlit App
Dados reais via football-data.org API (plano gratuito + pago)

Configure sua chave no Streamlit Cloud em:
  Settings → Secrets → adicione:
  FOOTBALL_API_KEY = "sua_chave_aqui"

Ou localmente crie o arquivo .streamlit/secrets.toml com:
  FOOTBALL_API_KEY = "sua_chave_aqui"
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ Football Stats",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; }
  .main { background: #0d1117; }
  .section-header {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 22px;
    color: #f0f6fc;
    border-left: 4px solid #238636;
    padding-left: 12px;
    margin: 24px 0 12px 0;
    letter-spacing: 1px;
  }
  div[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px;
  }
  div[data-testid="stMetricValue"] { color: #f0f6fc !important; font-size: 28px !important; }
  div[data-testid="stMetricLabel"] { color: #8b949e !important; }
  .stSelectbox > div > div { background: #161b22 !important; border-color: #30363d !important; }
</style>
""", unsafe_allow_html=True)

# ── Plotly dark theme ──────────────────────────────────────────────────────────
PLOTLY_THEME = {
    "paper_bgcolor": "#0d1117",
    "plot_bgcolor":  "#161b22",
    "font_color":    "#c9d1d9",
    "gridcolor":     "#21262d",
}

def styled_fig(fig):
    fig.update_layout(
        paper_bgcolor=PLOTLY_THEME["paper_bgcolor"],
        plot_bgcolor =PLOTLY_THEME["plot_bgcolor"],
        font=dict(color=PLOTLY_THEME["font_color"], family="Inter"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor=PLOTLY_THEME["gridcolor"], zerolinecolor=PLOTLY_THEME["gridcolor"])
    fig.update_yaxes(gridcolor=PLOTLY_THEME["gridcolor"], zerolinecolor=PLOTLY_THEME["gridcolor"])
    return fig

# ── API Config ─────────────────────────────────────────────────────────────────
API_BASE = "https://api.football-data.org/v4"

def get_api_key() -> str:
    try:
        return st.secrets["FOOTBALL_API_KEY"]
    except Exception:
        return ""

def api_get(endpoint: str, params: dict = None):
    key = get_api_key()
    if not key:
        return None
    headers = {"X-Auth-Token": key}
    try:
        r = requests.get(f"{API_BASE}{endpoint}", headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 403:
            st.error("Chave de API inválida ou sem permissão para este recurso.")
        elif r.status_code == 429:
            st.warning("Limite de requisições atingido. Aguarde um momento e tente novamente.")
        else:
            st.error(f"Erro na API: {r.status_code} — {r.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão: {e}")
        return None

# ── Leagues ────────────────────────────────────────────────────────────────────
LEAGUES = {
    "🇧🇷 Brasileirão Série A": {"id": 2013, "flag": "🇧🇷", "free": True},
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League":       {"id": 2021, "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "free": True},
    "🇪🇸 La Liga":              {"id": 2014, "flag": "🇪🇸", "free": True},
    "🇩🇪 Bundesliga":           {"id": 2002, "flag": "🇩🇪", "free": True},
    "🇫🇷 Ligue 1":              {"id": 2015, "flag": "🇫🇷", "free": False},
    "🇵🇹 Liga Portugal":        {"id": 2017, "flag": "🇵🇹", "free": False},
}

# ── API Data Functions ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_standings(league_id: int) -> pd.DataFrame:
    data = api_get(f"/competitions/{league_id}/standings")
    if not data:
        return pd.DataFrame()
    rows = []
    for entry in data["standings"][0]["table"]:
        team = entry["team"]
        rows.append({
            "Pos":     entry["position"],
            "Time":    team["name"],
            "PJ":      entry["playedGames"],
            "V":       entry["won"],
            "E":       entry["draw"],
            "D":       entry["lost"],
            "GP":      entry["goalsFor"],
            "GC":      entry["goalsAgainst"],
            "SG":      entry["goalDifference"],
            "Pts":     entry["points"],
            "team_id": team["id"],
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def fetch_top_scorers(league_id: int, limit: int = 10) -> pd.DataFrame:
    data = api_get(f"/competitions/{league_id}/scorers", params={"limit": limit})
    if not data:
        return pd.DataFrame()
    rows = []
    for s in data.get("scorers", []):
        player = s["player"]
        team   = s.get("team", {})
        rows.append({
            "Jogador":      player["name"],
            "Time":         team.get("name", "—"),
            "Gols":         s.get("goals", 0) or 0,
            "Assistências": s.get("assists", 0) or 0,
            "Partidas":     s.get("playedMatches", 0) or 0,
            "Pênaltis":     s.get("penalties", 0) or 0,
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def fetch_matches(league_id: int, status: str = "FINISHED", limit: int = 30) -> pd.DataFrame:
    data = api_get(f"/competitions/{league_id}/matches", params={"status": status})
    if not data:
        return pd.DataFrame()
    matches = data.get("matches", [])
    if status == "FINISHED":
        matches = matches[-limit:]
    else:
        matches = matches[:limit]
    rows = []
    for m in matches:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        score = m.get("score", {})
        ft    = score.get("fullTime", {})
        gh = ft.get("home")
        ga = ft.get("away")
        rows.append({
            "Data":       m["utcDate"][:10],
            "Casa":       home,
            "Fora":       away,
            "Placar":     f"{gh} – {ga}" if gh is not None else "—",
            "Gols Casa":  gh if gh is not None else 0,
            "Gols Fora":  ga if ga is not None else 0,
            "Rodada":     m.get("matchday", ""),
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def fetch_team_matches(league_id: int, team_id: int) -> pd.DataFrame:
    data = api_get(f"/competitions/{league_id}/matches", params={"status": "FINISHED"})
    if not data:
        return pd.DataFrame()
    rows = []
    for m in data.get("matches", []):
        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]
        if team_id not in (home_id, away_id):
            continue
        score = m.get("score", {})
        ft    = score.get("fullTime", {})
        gh = ft.get("home")
        ga = ft.get("away")
        if gh is None:
            continue
        is_home = (home_id == team_id)
        gf = gh if is_home else ga
        gc = ga if is_home else gh
        opp = m["awayTeam"]["name"] if is_home else m["homeTeam"]["name"]
        result = "V" if gf > gc else ("E" if gf == gc else "D")
        rows.append({
            "Data":       m["utcDate"][:10],
            "Adversário": opp,
            "Mando":      "Casa" if is_home else "Fora",
            "Placar":     f"{gf} – {gc}",
            "GF":         gf,
            "GC":         gc,
            "Resultado":  result,
            "Rodada":     m.get("matchday", ""),
        })
    return pd.DataFrame(rows).sort_values("Data").tail(15)

@st.cache_data(ttl=3600)
def fetch_upcoming_matches(league_id: int, limit: int = 20) -> pd.DataFrame:
    data = api_get(f"/competitions/{league_id}/matches", params={"status": "SCHEDULED"})
    if not data:
        return pd.DataFrame()
    rows = []
    for m in data.get("matches", [])[:limit]:
        try:
            dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
            data_fmt = dt.strftime("%d/%m %H:%M UTC")
        except Exception:
            data_fmt = m["utcDate"][:10]
        rows.append({
            "Data":    data_fmt,
            "Casa":    m["homeTeam"]["name"],
            "Fora":    m["awayTeam"]["name"],
            "Rodada":  m.get("matchday", "—"),
        })
    return pd.DataFrame(rows)

# ── API key check ──────────────────────────────────────────────────────────────
api_key = get_api_key()
if not api_key:
    st.error("## 🔑 Chave de API não encontrada")
    st.markdown("""
Para usar este app com dados reais, você precisa de uma chave gratuita do **football-data.org**.

**Como configurar:**

1. Crie uma conta gratuita em [football-data.org/client/register](https://www.football-data.org/client/register)
2. Copie sua chave de API no painel da conta

**No Streamlit Cloud:**
- Vá em **Settings → Secrets** e adicione:
```toml
FOOTBALL_API_KEY = "sua_chave_aqui"
```

**Localmente:**
- Crie o arquivo `.streamlit/secrets.toml` com:
```toml
FOOTBALL_API_KEY = "sua_chave_aqui"
```
""")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Football Stats")
    st.markdown("---")

    page = st.radio(
        "Navegação",
        ["📊 Classificação", "🏆 Comparar Times", "📋 Artilheiros", "📅 Partidas", "🔜 Próximos Jogos"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    league_name = st.selectbox("Liga", list(LEAGUES.keys()))
    league      = LEAGUES[league_name]
    league_id   = league["id"]

    if not league["free"]:
        st.warning("⚠️ Esta liga requer plano pago na football-data.org")

    st.markdown("---")
    st.caption("Dados: football-data.org · Cache: 1h")

# ── Pages ──────────────────────────────────────────────────────────────────────

# ── 1. Classificação ──────────────────────────────────────────────────────────
if "Classificação" in page:
    st.title(f"{league['flag']} Classificação · {league_name.split(' ', 1)[1]}")

    with st.spinner("Buscando classificação..."):
        df_stand = fetch_standings(league_id)

    if df_stand.empty:
        st.info("Não foi possível carregar os dados. Verifique sua chave de API.")
        st.stop()

    leader          = df_stand.iloc[0]
    last            = df_stand.iloc[-1]
    most_goals_row  = df_stand.loc[df_stand["GP"].idxmax()]
    best_defense    = df_stand.loc[df_stand["GC"].idxmin()]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🥇 Líder",          leader["Time"],           f"{leader['Pts']} pts")
    c2.metric("⚽ Maior Ataque",   most_goals_row["Time"],    f"{most_goals_row['GP']} gols")
    c3.metric("🛡️ Melhor Defesa",  best_defense["Time"],      f"{best_defense['GC']} sofridos")
    c4.metric("📉 Lanterna",       last["Time"],              f"{last['Pts']} pts")

    st.markdown("<div class='section-header'>Tabela de Classificação</div>", unsafe_allow_html=True)

    def highlight_zones(row):
        pos   = row["Pos"]
        total = len(df_stand)
        if pos <= 4:
            return ["background-color: #0d2d0d; color: #3fb950"] * len(row)
        if pos <= 6:
            return ["background-color: #1a1a0d; color: #e3b341"] * len(row)
        if pos >= total - 2:
            return ["background-color: #2d0d0d; color: #f85149"] * len(row)
        return [""] * len(row)

    display_cols = ["Pos", "Time", "PJ", "V", "E", "D", "GP", "GC", "SG", "Pts"]
    st.dataframe(
        df_stand[display_cols].style.apply(highlight_zones, axis=1),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("🟢 Fase de grupos UEFA · 🟡 Liga Europa/Conference · 🔴 Rebaixamento")

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-header'>Gols Marcados (Top 10)</div>", unsafe_allow_html=True)
        top10 = df_stand.nlargest(10, "GP")
        fig_gf = px.bar(
            top10, x="GP", y="Time", orientation="h",
            color="GP", color_continuous_scale=["#0d4429", "#3fb950"],
            labels={"GP": "Gols", "Time": ""},
        )
        fig_gf.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
        st.plotly_chart(styled_fig(fig_gf), use_container_width=True)

    with col_r:
        st.markdown("<div class='section-header'>Pontos (Top 10)</div>", unsafe_allow_html=True)
        top10p = df_stand.nlargest(10, "Pts")
        fig_pts = px.bar(
            top10p, x="Pts", y="Time", orientation="h",
            color="Pts", color_continuous_scale=["#0d2d5e", "#1f6feb"],
            labels={"Pts": "Pontos", "Time": ""},
        )
        fig_pts.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
        st.plotly_chart(styled_fig(fig_pts), use_container_width=True)

    st.markdown("<div class='section-header'>Vitórias × Derrotas</div>", unsafe_allow_html=True)
    fig_sc = px.scatter(
        df_stand, x="D", y="V", size="Pts", text="Time",
        color="Pts", color_continuous_scale="Greens",
        labels={"D": "Derrotas", "V": "Vitórias"},
    )
    fig_sc.update_traces(textposition="top center")
    st.plotly_chart(styled_fig(fig_sc), use_container_width=True)

# ── 2. Comparar Times ─────────────────────────────────────────────────────────
elif "Comparar" in page:
    st.title(f"🏆 Comparação de Times · {league_name.split(' ', 1)[1]}")

    with st.spinner("Buscando dados..."):
        df_stand = fetch_standings(league_id)

    if df_stand.empty:
        st.info("Não foi possível carregar os dados.")
        st.stop()

    team_names = df_stand["Time"].tolist()
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        t1 = st.selectbox("Time 1", team_names, index=0)
    with col_s2:
        default_idx = 1 if len(team_names) > 1 else 0
        t2 = st.selectbox("Time 2", team_names, index=default_idx)

    r1 = df_stand[df_stand["Time"] == t1].iloc[0]
    r2 = df_stand[df_stand["Time"] == t2].iloc[0]

    st.markdown("<div class='section-header'>Comparativo de Indicadores</div>", unsafe_allow_html=True)
    metrics = [
        ("Pontos", "Pts"), ("Vitórias", "V"), ("Empates", "E"), ("Derrotas", "D"),
        ("Gols Marcados", "GP"), ("Gols Sofridos", "GC"), ("Saldo de Gols", "SG"),
    ]
    labels = [m[0] for m in metrics]
    vals1  = [int(r1[m[1]]) for m in metrics]
    vals2  = [int(r2[m[1]]) for m in metrics]

    fig_cmp = go.Figure()
    fig_cmp.add_bar(name=t1, x=labels, y=vals1, marker_color="#238636")
    fig_cmp.add_bar(name=t2, x=labels, y=vals2, marker_color="#1f6feb")
    fig_cmp.update_layout(barmode="group", xaxis_tickangle=-20, legend=dict(orientation="h"))
    st.plotly_chart(styled_fig(fig_cmp), use_container_width=True)

    st.markdown("<div class='section-header'>Tabela Comparativa</div>", unsafe_allow_html=True)
    cmp_rows = []
    for label, key in metrics:
        v1, v2 = int(r1[key]), int(r2[key])
        if key == "GC" or key == "D":
            melhor = t1 if v1 < v2 else (t2 if v2 < v1 else "Igual")
        else:
            melhor = t1 if v1 > v2 else (t2 if v2 > v1 else "Igual")
        cmp_rows.append({"Métrica": label, t1: v1, t2: v2, "Melhor": melhor})
    st.dataframe(pd.DataFrame(cmp_rows), use_container_width=True, hide_index=True)

    st.markdown("<div class='section-header'>Radar Comparativo</div>", unsafe_allow_html=True)
    radar_keys = ["V", "E", "GP", "SG", "Pts"]
    radar_lbls = ["Vitórias", "Empates", "Gols", "Saldo", "Pontos"]
    rv1 = [int(r1[k]) for k in radar_keys]
    rv2 = [int(r2[k]) for k in radar_keys]
    fig_r = go.Figure()
    for name, rv, color in [(t1, rv1, "#238636"), (t2, rv2, "#1f6feb")]:
        fig_r.add_trace(go.Scatterpolar(
            r=rv + [rv[0]], theta=radar_lbls + [radar_lbls[0]],
            fill="toself", name=name,
            fillcolor=f"{color}33",
            line=dict(color=color, width=2),
        ))
    fig_r.update_layout(
        polar=dict(
            bgcolor="#161b22",
            radialaxis=dict(visible=True, color="#8b949e"),
            angularaxis=dict(color="#8b949e"),
        ),
        legend=dict(orientation="h", y=-0.1),
    )
    st.plotly_chart(styled_fig(fig_r), use_container_width=True)

# ── 3. Artilheiros ────────────────────────────────────────────────────────────
elif "Artilheiros" in page:
    st.title(f"📋 Artilheiros · {league_name.split(' ', 1)[1]}")

    limit = st.slider("Número de jogadores", 5, 20, 10)

    with st.spinner("Buscando artilheiros..."):
        df_sc = fetch_top_scorers(league_id, limit)

    if df_sc.empty:
        st.info("Não foi possível carregar os artilheiros.")
        st.stop()

    fig_sc = px.bar(
        df_sc, x="Jogador", y="Gols",
        color="Assistências",
        color_continuous_scale=["#0d4429", "#3fb950"],
        text="Gols",
        hover_data=["Time", "Partidas", "Pênaltis"],
    )
    fig_sc.update_traces(textposition="outside")
    fig_sc.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(styled_fig(fig_sc), use_container_width=True)

    st.markdown("<div class='section-header'>Tabela Completa</div>", unsafe_allow_html=True)

    def highlight_top(row):
        if row.name == 0:
            return ["background-color: #0d4429; color: #56d364"] * len(row)
        if row.name == 1:
            return ["background-color: #0d2d1a; color: #3fb950"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_sc.style.apply(highlight_top, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    if df_sc["Assistências"].sum() > 0:
        st.markdown("<div class='section-header'>Gols × Assistências</div>", unsafe_allow_html=True)
        fig_scat = px.scatter(
            df_sc, x="Assistências", y="Gols", text="Jogador",
            size="Partidas", color="Gols",
            color_continuous_scale="Greens",
        )
        fig_scat.update_traces(textposition="top center")
        st.plotly_chart(styled_fig(fig_scat), use_container_width=True)

# ── 4. Partidas ───────────────────────────────────────────────────────────────
elif "Partidas" in page:
    st.title(f"📅 Partidas Recentes · {league_name.split(' ', 1)[1]}")

    with st.spinner("Buscando partidas..."):
        df_matches = fetch_matches(league_id, status="FINISHED", limit=30)

    if df_matches.empty:
        st.info("Nenhuma partida finalizada encontrada.")
        st.stop()

    all_teams = sorted(set(df_matches["Casa"].tolist() + df_matches["Fora"].tolist()))
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        team_filter = st.selectbox("Filtrar por time (opcional)", ["Todos"] + all_teams)
    with col_f2:
        rodadas = sorted([r for r in df_matches["Rodada"].dropna().unique() if r != ""], key=lambda x: int(x) if str(x).isdigit() else x)
        round_filter = st.selectbox("Rodada", ["Todas"] + [str(r) for r in rodadas])

    df_view = df_matches.copy()
    if team_filter != "Todos":
        df_view = df_view[(df_view["Casa"] == team_filter) | (df_view["Fora"] == team_filter)]
    if round_filter != "Todas":
        df_view = df_view[df_view["Rodada"].astype(str) == round_filter]

    st.dataframe(df_view.drop(columns=["Gols Casa", "Gols Fora"]), use_container_width=True, hide_index=True)

    st.markdown("<div class='section-header'>Total de Gols por Rodada</div>", unsafe_allow_html=True)
    df_rnd = df_matches.copy()
    df_rnd["Total Gols"] = df_rnd["Gols Casa"] + df_rnd["Gols Fora"]
    agg_round = df_rnd.groupby("Rodada").agg(
        Gols=("Total Gols", "sum"),
        Partidas=("Total Gols", "count")
    ).reset_index()
    agg_round["Média"] = (agg_round["Gols"] / agg_round["Partidas"]).round(2)
    agg_round = agg_round.sort_values("Rodada")

    fig_rnd = go.Figure()
    fig_rnd.add_bar(x=agg_round["Rodada"], y=agg_round["Gols"],
                    name="Total de Gols", marker_color="#238636")
    fig_rnd.add_scatter(x=agg_round["Rodada"], y=agg_round["Média"],
                        name="Média por Jogo", mode="lines+markers",
                        line=dict(color="#e3b341", width=2))
    fig_rnd.update_layout(legend=dict(orientation="h"))
    st.plotly_chart(styled_fig(fig_rnd), use_container_width=True)

    # Per-team performance when filtered
    if team_filter != "Todos":
        with st.spinner("Buscando histórico do time..."):
            df_stand_tmp = fetch_standings(league_id)
        if not df_stand_tmp.empty:
            row_team = df_stand_tmp[df_stand_tmp["Time"] == team_filter]
            if not row_team.empty:
                team_id = int(row_team.iloc[0]["team_id"])
                df_team_m = fetch_team_matches(league_id, team_id)
                if not df_team_m.empty:
                    st.markdown(f"<div class='section-header'>Sequência Recente — {team_filter}</div>", unsafe_allow_html=True)
                    wins   = (df_team_m["Resultado"] == "V").sum()
                    draws  = (df_team_m["Resultado"] == "E").sum()
                    losses = (df_team_m["Resultado"] == "D").sum()
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Partidas",        len(df_team_m))
                    c2.metric("✅ Vitórias",      int(wins))
                    c3.metric("⚽ Gols Marcados", int(df_team_m["GF"].sum()))
                    c4.metric("🛡 Gols Sofridos", int(df_team_m["GC"].sum()))

                    color_map = {"V": "#238636", "E": "#e3b341", "D": "#da3633"}
                    df_team_m["Cor"] = df_team_m["Resultado"].map(color_map)
                    df_team_m["Num"] = df_team_m["Resultado"].map({"V": 3, "E": 1, "D": 0})

                    fig_seq = go.Figure()
                    for _, row in df_team_m.iterrows():
                        fig_seq.add_bar(
                            x=[f"R{row['Rodada']} {row['Adversário'][:12]}"],
                            y=[row["Num"]],
                            marker_color=row["Cor"],
                            showlegend=False,
                            text=row["Placar"],
                            textposition="outside",
                        )
                    fig_seq.update_layout(
                        yaxis=dict(tickvals=[0, 1, 3], ticktext=["Derrota", "Empate", "Vitória"]),
                        xaxis_tickangle=-30,
                    )
                    st.plotly_chart(styled_fig(fig_seq), use_container_width=True)

# ── 5. Próximos Jogos ─────────────────────────────────────────────────────────
elif "Próximos" in page:
    st.title(f"🔜 Próximos Jogos · {league_name.split(' ', 1)[1]}")

    with st.spinner("Buscando agenda..."):
        df_next = fetch_upcoming_matches(league_id, limit=30)

    if df_next.empty:
        st.info("Nenhuma partida agendada encontrada (a temporada pode ter encerrado ou não iniciada).")
        st.stop()

    all_upcoming = sorted(set(df_next["Casa"].tolist() + df_next["Fora"].tolist()))
    team_up = st.selectbox("Filtrar por time", ["Todos"] + all_upcoming)

    df_show = df_next.copy()
    if team_up != "Todos":
        df_show = df_show[(df_show["Casa"] == team_up) | (df_show["Fora"] == team_up)]

    st.dataframe(df_show, use_container_width=True, hide_index=True)

    if not df_show.empty:
        st.markdown("<div class='section-header'>Partidas por Rodada</div>", unsafe_allow_html=True)
        round_counts = df_next["Rodada"].value_counts().reset_index()
        round_counts.columns = ["Rodada", "Jogos"]
        round_counts = round_counts.sort_values("Rodada")
        fig_rnd2 = px.bar(
            round_counts, x="Rodada", y="Jogos",
            color="Jogos", color_continuous_scale=["#0d2d5e", "#1f6feb"],
        )
        st.plotly_chart(styled_fig(fig_rnd2), use_container_width=True)
