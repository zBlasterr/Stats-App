import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ Football Stats",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; }

  .main { background: #0d1117; }

  .metric-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }
  .metric-card .label {
    color: #8b949e;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
  }
  .metric-card .value {
    color: #f0f6fc;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 36px;
    letter-spacing: 2px;
  }
  .metric-card .sub {
    color: #3fb950;
    font-size: 12px;
  }

  .stSelectbox > div > div { background: #161b22 !important; border-color: #30363d !important; }
  .stSlider > div { color: #8b949e; }

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
</style>
""", unsafe_allow_html=True)

# ── Data (embedded – no API key needed) ──────────────────────────────────────

TEAMS = {
    "Real Madrid": "🇪🇸",
    "Barcelona": "🇪🇸",
    "Manchester City": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Liverpool": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Bayern Munich": "🇩🇪",
    "PSG": "🇫🇷",
    "Juventus": "🇮🇹",
    "Chelsea": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Arsenal": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Borussia Dortmund": "🇩🇪",
    "Atlético Madrid": "🇪🇸",
    "Inter Milan": "🇮🇹",
    "Flamengo": "🇧🇷",
    "Palmeiras": "🇧🇷",
    "São Paulo": "🇧🇷",
}

@st.cache_data
def get_team_stats(team_name: str) -> dict:
    """Returns simulated team stats (replace with real API call if desired)."""
    import hashlib, math
    seed = int(hashlib.md5(team_name.encode()).hexdigest(), 16) % 1000
    rng = __import__("random").Random(seed)

    matches = 34
    wins    = rng.randint(18, 28)
    draws   = rng.randint(3, 8)
    losses  = matches - wins - draws
    gf      = rng.randint(50, 95)
    ga      = rng.randint(20, 55)
    pts     = wins * 3 + draws

    return {
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_diff": gf - ga,
        "points": pts,
        "clean_sheets": rng.randint(8, 20),
        "yellow_cards": rng.randint(40, 80),
        "red_cards": rng.randint(2, 8),
        "possession_avg": round(rng.uniform(44, 66), 1),
        "shots_pg": round(rng.uniform(10, 18), 1),
        "pass_accuracy": round(rng.uniform(78, 92), 1),
    }

@st.cache_data
def get_top_scorers(team_name: str) -> pd.DataFrame:
    import random
    rng = random.Random(hash(team_name) % 9999)
    names = [
        "Carlos Silva", "João Pedro", "Marcos Nunes", "Lucas Alves",
        "Rafael Costa", "André Martins", "Felipe Souza", "Rodrigo Lima",
        "Thiago Rocha", "Bruno Ferreira",
    ]
    rng.shuffle(names)
    data = []
    goals_pool = sorted([rng.randint(2, 28) for _ in range(6)], reverse=True)
    assists_pool = sorted([rng.randint(1, 16) for _ in range(6)], reverse=True)
    for i in range(6):
        data.append({
            "Player": names[i],
            "Goals": goals_pool[i],
            "Assists": assists_pool[i],
            "Matches": rng.randint(20, 34),
            "Avg Rating": round(rng.uniform(6.5, 9.2), 1),
        })
    return pd.DataFrame(data)

@st.cache_data
def get_monthly_goals(team_name: str) -> pd.DataFrame:
    import random
    rng = random.Random(hash(team_name + "monthly") % 9999)
    months = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May"]
    return pd.DataFrame({
        "Month": months,
        "Goals Scored": [rng.randint(4, 14) for _ in months],
        "Goals Conceded": [rng.randint(2, 9) for _ in months],
    })

@st.cache_data
def get_match_results(team_name: str) -> pd.DataFrame:
    import random, datetime
    rng = random.Random(hash(team_name + "results") % 9999)
    opponents = list(TEAMS.keys())
    opponents = [t for t in opponents if t != team_name]
    results = []
    date = datetime.date(2024, 8, 10)
    for i in range(10):
        opp = rng.choice(opponents)
        gf = rng.randint(0, 5)
        ga = rng.randint(0, 4)
        outcome = "W" if gf > ga else ("D" if gf == ga else "L")
        results.append({
            "Date": date.strftime("%d/%m/%Y"),
            "Opponent": opp,
            "Score": f"{gf} – {ga}",
            "Result": outcome,
            "Venue": rng.choice(["Home", "Away"]),
        })
        date += datetime.timedelta(days=rng.randint(5, 10))
    return pd.DataFrame(results)

# ── Helpers ───────────────────────────────────────────────────────────────────

PLOTLY_THEME = {
    "paper_bgcolor": "#0d1117",
    "plot_bgcolor": "#161b22",
    "font_color": "#c9d1d9",
    "gridcolor": "#21262d",
}

def styled_fig(fig):
    fig.update_layout(
        paper_bgcolor=PLOTLY_THEME["paper_bgcolor"],
        plot_bgcolor=PLOTLY_THEME["plot_bgcolor"],
        font=dict(color=PLOTLY_THEME["font_color"], family="Inter"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor=PLOTLY_THEME["gridcolor"], zerolinecolor=PLOTLY_THEME["gridcolor"])
    fig.update_yaxes(gridcolor=PLOTLY_THEME["gridcolor"], zerolinecolor=PLOTLY_THEME["gridcolor"])
    return fig

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚽ Football Stats")
    st.markdown("---")

    page = st.radio(
        "Navegação",
        ["📊 Visão Geral", "🏆 Comparar Times", "📋 Artilheiros", "📅 Resultados"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    team1 = st.selectbox(
        "Time Principal",
        list(TEAMS.keys()),
        format_func=lambda t: f"{TEAMS[t]}  {t}",
    )

    if "Comparar" in page:
        team2 = st.selectbox(
            "Time Adversário",
            [t for t in TEAMS if t != team1],
            format_func=lambda t: f"{TEAMS[t]}  {t}",
        )

    st.markdown("---")
    st.caption("Dados simulados para demonstração. Substitua por uma API real como football-data.org ou API-Football.")

# ── Pages ─────────────────────────────────────────────────────────────────────

# ── 1. Visão Geral ────────────────────────────────────────────────────────────
if "Visão" in page:
    stats = get_team_stats(team1)
    flag  = TEAMS[team1]

    st.title(f"{flag}  {team1}")
    st.markdown(f"<p style='color:#8b949e;margin-top:-12px'>Temporada 2024/25 · Estatísticas gerais</p>", unsafe_allow_html=True)

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pontos", stats["points"])
    c2.metric("Vitórias", stats["wins"])
    c3.metric("Gols Marcados", stats["goals_for"])
    c4.metric("Gols Sofridos", stats["goals_against"])
    c5.metric("Saldo de Gols", f"+{stats['goal_diff']}" if stats["goal_diff"] >= 0 else str(stats["goal_diff"]))

    st.markdown("<div class='section-header'>Gols por Mês</div>", unsafe_allow_html=True)
    monthly = get_monthly_goals(team1)
    fig_monthly = go.Figure()
    fig_monthly.add_bar(x=monthly["Month"], y=monthly["Goals Scored"],
                        name="Marcados", marker_color="#238636")
    fig_monthly.add_bar(x=monthly["Month"], y=monthly["Goals Conceded"],
                        name="Sofridos", marker_color="#da3633")
    fig_monthly.update_layout(barmode="group", legend=dict(orientation="h"))
    st.plotly_chart(styled_fig(fig_monthly), use_container_width=True)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("<div class='section-header'>Resultados (Pizza)</div>", unsafe_allow_html=True)
        fig_pie = px.pie(
            values=[stats["wins"], stats["draws"], stats["losses"]],
            names=["Vitórias", "Empates", "Derrotas"],
            color_discrete_sequence=["#238636", "#e3b341", "#da3633"],
            hole=0.4,
        )
        fig_pie.update_traces(textfont_size=13)
        st.plotly_chart(styled_fig(fig_pie), use_container_width=True)

    with col_r:
        st.markdown("<div class='section-header'>Indicadores Táticos</div>", unsafe_allow_html=True)
        radar_cats = ["Posse (%)", "Chutes/Jogo", "Passes (%)", "Clean Sheets", "Cartões Amarelos"]
        radar_vals = [
            stats["possession_avg"],
            stats["shots_pg"] * 5,   # normalised to ~100
            stats["pass_accuracy"],
            stats["clean_sheets"] * 5,
            100 - stats["yellow_cards"],
        ]
        fig_radar = go.Figure(go.Scatterpolar(
            r=radar_vals + [radar_vals[0]],
            theta=radar_cats + [radar_cats[0]],
            fill="toself",
            fillcolor="rgba(35,134,54,0.25)",
            line=dict(color="#3fb950", width=2),
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="#161b22",
                radialaxis=dict(visible=True, range=[0, 110], color="#8b949e"),
                angularaxis=dict(color="#8b949e"),
            )
        )
        st.plotly_chart(styled_fig(fig_radar), use_container_width=True)

    st.markdown("<div class='section-header'>Detalhes da Temporada</div>", unsafe_allow_html=True)
    d1, d2, d3 = st.columns(3)
    d1.metric("Posse Média", f"{stats['possession_avg']}%")
    d2.metric("Chutes por Jogo", stats["shots_pg"])
    d3.metric("Precisão de Passe", f"{stats['pass_accuracy']}%")
    d4, d5, d6 = st.columns(3)
    d4.metric("Clean Sheets", stats["clean_sheets"])
    d5.metric("Cartões Amarelos", stats["yellow_cards"])
    d6.metric("Cartões Vermelhos", stats["red_cards"])


# ── 2. Comparar Times ─────────────────────────────────────────────────────────
elif "Comparar" in page:
    s1 = get_team_stats(team1)
    s2 = get_team_stats(team2)

    st.title("🏆 Comparação de Times")
    col1, col2 = st.columns(2)
    col1.markdown(f"### {TEAMS[team1]} {team1}")
    col2.markdown(f"### {TEAMS[team2]} {team2}")

    metrics = [
        ("Pontos",          "points"),
        ("Vitórias",        "wins"),
        ("Gols Marcados",   "goals_for"),
        ("Gols Sofridos",   "goals_against"),
        ("Posse Média (%)", "possession_avg"),
        ("Precisão de Passe (%)", "pass_accuracy"),
        ("Chutes/Jogo",     "shots_pg"),
        ("Clean Sheets",    "clean_sheets"),
    ]

    st.markdown("<div class='section-header'>Comparativo de Indicadores</div>", unsafe_allow_html=True)

    labels = [m[0] for m in metrics]
    vals1  = [s1[m[1]] for m in metrics]
    vals2  = [s2[m[1]] for m in metrics]

    fig_bar = go.Figure()
    fig_bar.add_bar(name=team1, x=labels, y=vals1, marker_color="#238636")
    fig_bar.add_bar(name=team2, x=labels, y=vals2, marker_color="#1f6feb")
    fig_bar.update_layout(barmode="group", xaxis_tickangle=-30)
    st.plotly_chart(styled_fig(fig_bar), use_container_width=True)

    st.markdown("<div class='section-header'>Tabela Comparativa</div>", unsafe_allow_html=True)
    rows = []
    for label, key in metrics:
        v1, v2 = s1[key], s2[key]
        winner = team1 if v1 > v2 else (team2 if v2 > v1 else "Empate")
        rows.append({"Métrica": label, team1: v1, team2: v2, "Melhor": winner})
    df_cmp = pd.DataFrame(rows)
    st.dataframe(df_cmp, use_container_width=True, hide_index=True)

    # Mini radar comparison
    st.markdown("<div class='section-header'>Radar Comparativo</div>", unsafe_allow_html=True)
    r_cats = ["Posse", "Chutes", "Passes", "Clean Sheets", "Gols"]
    r1 = [s1["possession_avg"], s1["shots_pg"]*5, s1["pass_accuracy"], s1["clean_sheets"]*5, s1["goals_for"]]
    r2 = [s2["possession_avg"], s2["shots_pg"]*5, s2["pass_accuracy"], s2["clean_sheets"]*5, s2["goals_for"]]
    fig_r2 = go.Figure()
    for name, r, color in [(team1, r1, "#238636"), (team2, r2, "#1f6feb")]:
        fig_r2.add_trace(go.Scatterpolar(
            r=r + [r[0]], theta=r_cats + [r_cats[0]],
            fill="toself", name=name,
            fillcolor=color.replace("#", "rgba(").rstrip(")") + ",0.18)" if False else f"{color}33",
            line=dict(color=color, width=2),
        ))
    fig_r2.update_layout(
        polar=dict(
            bgcolor="#161b22",
            radialaxis=dict(visible=True, range=[0, 110], color="#8b949e"),
            angularaxis=dict(color="#8b949e"),
        ),
        legend=dict(orientation="h", y=-0.1),
    )
    st.plotly_chart(styled_fig(fig_r2), use_container_width=True)


# ── 3. Artilheiros ────────────────────────────────────────────────────────────
elif "Artilheiros" in page:
    st.title(f"📋 Artilheiros – {TEAMS[team1]} {team1}")
    df_sc = get_top_scorers(team1)

    # Bar chart
    fig_sc = px.bar(
        df_sc, x="Player", y="Goals",
        color="Assists",
        color_continuous_scale=["#238636", "#3fb950", "#56d364"],
        labels={"Goals": "Gols", "Assists": "Assistências"},
        text="Goals",
    )
    fig_sc.update_traces(textposition="outside")
    st.plotly_chart(styled_fig(fig_sc), use_container_width=True)

    # Table with conditional formatting
    st.markdown("<div class='section-header'>Tabela de Artilheiros</div>", unsafe_allow_html=True)

    def highlight_top(row):
        if row.name == 0:
            return ["background-color: #0d4429; color: #56d364"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_sc.style.apply(highlight_top, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # Scatter: Goals vs Assists
    st.markdown("<div class='section-header'>Gols × Assistências</div>", unsafe_allow_html=True)
    fig_scat = px.scatter(
        df_sc, x="Assists", y="Goals", text="Player",
        size="Matches", color="Avg Rating",
        color_continuous_scale="Greens",
        labels={"Goals": "Gols", "Assists": "Assistências"},
    )
    fig_scat.update_traces(textposition="top center")
    st.plotly_chart(styled_fig(fig_scat), use_container_width=True)


# ── 4. Resultados ─────────────────────────────────────────────────────────────
elif "Resultados" in page:
    st.title(f"📅 Últimos Resultados – {TEAMS[team1]} {team1}")
    df_res = get_match_results(team1)

    # Summary
    wins   = (df_res["Result"] == "W").sum()
    draws  = (df_res["Result"] == "D").sum()
    losses = (df_res["Result"] == "L").sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Vitórias", wins)
    c2.metric("🟡 Empates", draws)
    c3.metric("❌ Derrotas", losses)

    # Timeline chart
    st.markdown("<div class='section-header'>Sequência de Resultados</div>", unsafe_allow_html=True)
    color_map = {"W": "#238636", "D": "#e3b341", "L": "#da3633"}
    df_res["Color"] = df_res["Result"].map(color_map)
    df_res["NumResult"] = df_res["Result"].map({"W": 3, "D": 1, "L": 0})

    fig_res = go.Figure()
    for _, row in df_res.iterrows():
        fig_res.add_bar(
            x=[row["Opponent"]],
            y=[row["NumResult"]],
            marker_color=row["Color"],
            name=row["Result"],
            showlegend=False,
            text=row["Score"],
            textposition="outside",
        )
    fig_res.update_layout(yaxis=dict(tickvals=[0, 1, 3], ticktext=["Derrota", "Empate", "Vitória"]))
    st.plotly_chart(styled_fig(fig_res), use_container_width=True)

    # Table
    st.markdown("<div class='section-header'>Tabela de Partidas</div>", unsafe_allow_html=True)

    def color_result(val):
        if val == "W": return "color: #3fb950; font-weight: bold"
        if val == "D": return "color: #e3b341; font-weight: bold"
        if val == "L": return "color: #f85149; font-weight: bold"
        return ""

    st.dataframe(
        df_res.drop(columns=["Color", "NumResult"]).style.applymap(color_result, subset=["Result"]),
        use_container_width=True,
        hide_index=True,
    )
