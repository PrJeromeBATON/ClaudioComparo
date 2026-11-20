"""
Comparateur de cours : Bitcoin, Ethereum, Or et Argent
Lancer avec :  streamlit run app.py
"""

from datetime import date, timedelta

import json

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

try:  # autocomplétion « au fil de la frappe »
    from streamlit_searchbox import st_searchbox

    HAS_SEARCHBOX = True
except ImportError:
    HAS_SEARCHBOX = False

try:  # lecture / écriture du localStorage du navigateur
    from streamlit_js_eval import streamlit_js_eval

    HAS_JS_EVAL = True
except ImportError:
    HAS_JS_EVAL = False

st.set_page_config(page_title="Comparateur de cours", page_icon="📈", layout="wide")

# ----------------------------------------------------------------------------
# Configuration des actifs
# ----------------------------------------------------------------------------
ASSETS = {
    "Bitcoin (BTC)": {"ticker": "BTC-USD", "crypto": True},
    "Ethereum (ETH)": {"ticker": "ETH-USD", "crypto": True},
    "Or (once)": {"ticker": "GC=F", "crypto": False},
    "Argent (once)": {"ticker": "SI=F", "crypto": False},
}

PERIODS = {
    "1 mois": 30,
    "3 mois": 91,
    "6 mois": 182,
    "1 an": 365,
    "3 ans": 365 * 3,
    "5 ans": 365 * 5,
    "Personnalisé": None,
}


# ----------------------------------------------------------------------------
# Données
# ----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers: tuple, start: date, end: date):
    """Télécharge les cours de clôture (USD) ticker par ticker.

    Retourne (DataFrame des prix, dict des erreurs par ticker).
    """
    series, errors = {}, {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(
                start=start, end=end + timedelta(days=1), auto_adjust=True
            )
            if hist.empty:
                errors[t] = "aucune donnée renvoyée"
                continue
            s = hist["Close"].copy()
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            series[t] = s[~s.index.duplicated(keep="last")]
        except Exception as exc:
            errors[t] = str(exc)
    return pd.DataFrame(series), errors


def annualization_factor(is_crypto: bool) -> int:
    return 365 if is_crypto else 252


def max_drawdown(series: pd.Series) -> float:
    running_max = series.cummax()
    return ((series / running_max) - 1).min()


# ----------------------------------------------------------------------------
# Barre latérale
# ----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def _yahoo_search(query: str) -> list:
    try:
        return yf.Search(query, max_results=8).quotes or []
    except Exception:
        return []


def search_symbols(query: str) -> list:
    """Suggestions d'autocomplétion : liste de (libellé affiché, valeur JSON)."""
    query = (query or "").strip()
    if len(query) < 2:
        return []

    suggestions = []
    for q in _yahoo_search(query):
        symbol = q.get("symbol")
        if not symbol:
            continue
        name = q.get("shortname") or q.get("longname") or symbol
        exchange = q.get("exchDisp") or q.get("exchange") or ""
        label = f"{symbol} — {name}" + (f" · {exchange}" if exchange else "")
        value = {
            "symbol": symbol,
            "name": name,
            "crypto": q.get("quoteType") == "CRYPTOCURRENCY",
        }
        suggestions.append((label, json.dumps(value)))

    # Permet toujours d'utiliser directement le code saisi (ex. « AAPL », « SOL-USD »)
    code = query.upper()
    if not any(json.loads(v)["symbol"] == code for _, v in suggestions):
        direct = {"symbol": code, "name": code, "crypto": code.endswith("-USD")}
        suggestions.append((f"Utiliser le code « {code} »", json.dumps(direct)))
    return suggestions


# --- Liste d'actifs (persistée dans le localStorage du navigateur) -----------
STORAGE_KEY = "compare_assets_v1"
DEFAULT_WATCHLIST = [
    {"ticker": v["ticker"], "label": k, "crypto": v["crypto"]} for k, v in ASSETS.items()
]


def do_rerun():
    """st.rerun() n'existe que dans les versions récentes de Streamlit."""
    (getattr(st, "rerun", None) or st.experimental_rerun)()


def parse_watchlist(stored: str) -> list:
    """Interprète le contenu du localStorage ; valeurs par défaut si rien/invalide."""
    if stored == "EMPTY":  # jamais rien enregistré : première visite
        return list(DEFAULT_WATCHLIST)
    try:
        data = json.loads(stored)
        return [
            {"ticker": str(w["ticker"]), "label": str(w["label"]), "crypto": bool(w["crypto"])}
            for w in data
        ]
    except Exception:
        return list(DEFAULT_WATCHLIST)


def add_asset(info: dict):
    wl = st.session_state["watchlist"]
    if any(w["ticker"] == info["symbol"] for w in wl):
        return
    wl.append(
        {
            "ticker": info["symbol"],
            "label": f"{info['name']} ({info['symbol']})",
            "crypto": bool(info["crypto"]),
        }
    )


def remove_asset(ticker: str):
    st.session_state["watchlist"] = [
        w for w in st.session_state["watchlist"] if w["ticker"] != ticker
    ]


def reset_assets():
    st.session_state["watchlist"] = list(DEFAULT_WATCHLIST)


def add_from_fallback(value: str):
    add_asset(json.loads(value))
    st.session_state["search_text"] = ""


# Chargement initial : localStorage s'il existe, sinon valeurs par défaut (1re visite seulement)
if "watchlist" not in st.session_state:
    if HAS_JS_EVAL:
        # 'EMPTY' = rien en stockage ; None = le navigateur n'a pas encore répondu
        stored = streamlit_js_eval(
            js_expressions=f"localStorage.getItem('{STORAGE_KEY}') || 'EMPTY'",
            key="ls_get",
        )
        if stored is None:
            st.caption("Chargement de vos actifs…")
            st.stop()
        st.session_state["watchlist"] = parse_watchlist(stored)
    else:
        st.session_state["watchlist"] = list(DEFAULT_WATCHLIST)
    st.session_state["saved_json"] = None
    st.session_state["save_n"] = 0

st.session_state.setdefault("search_n", 0)

st.sidebar.title("Claudio Comparo\n⚙️ Paramètres")

# --- Ajout d'un actif par nom ou code ----------------------------------------
st.sidebar.markdown("**➕ Ajouter un actif**")
if HAS_SEARCHBOX:
    with st.sidebar:
        # La clé change après chaque ajout : le champ est ainsi vidé et on peut en ajouter autant qu'on veut.
        picked = st_searchbox(
            search_symbols,
            placeholder="Nom ou code : apple, tesla, SOL-USD…",
            key=f"asset_search_{st.session_state['search_n']}",
        )
    if picked:
        add_asset(json.loads(picked) if isinstance(picked, str) else picked)
        st.session_state["search_n"] += 1
        do_rerun()
else:
    q = st.sidebar.text_input("Nom ou code", placeholder="apple, tesla, SOL-USD…", key="search_text")
    found = dict(search_symbols(q)) if q else {}
    if found:
        choice = st.sidebar.selectbox("Résultats", list(found.keys()), key="search_choice")
        st.sidebar.button("Ajouter", on_click=add_from_fallback, args=(found[choice],))
    st.sidebar.caption("Astuce : `pip install streamlit-searchbox` pour l'autocomplétion en direct.")

# --- Liste des actifs comparés ------------------------------------------------
st.sidebar.markdown("**Actifs comparés**")
watchlist = st.session_state["watchlist"]
if not watchlist:
    st.sidebar.caption("Aucun actif : utilisez la recherche ci-dessus.")
for w in watchlist:
    c1, c2 = st.sidebar.columns([5, 1])
    c1.write(w["label"])
    c2.button("✕", key=f"rm_{w['ticker']}", on_click=remove_asset, args=(w["ticker"],), help="Retirer")
st.sidebar.button("↺ Valeurs par défaut", on_click=reset_assets)
st.sidebar.caption(
    "Les actifs ajoutés sont affichés dans leur devise de cotation d'origine "
    "(la conversion en € suppose des cours en USD)."
)

# --- Sauvegarde dans le localStorage ------------------------------------------
if HAS_JS_EVAL:
    payload = json.dumps(st.session_state["watchlist"], ensure_ascii=False)
    if payload != st.session_state["saved_json"]:
        st.session_state["saved_json"] = payload
        st.session_state["save_n"] += 1
    # Le composant reste affiché avec la même clé tant que rien ne change.
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('{STORAGE_KEY}', {json.dumps(st.session_state['saved_json'])})",
        key=f"ls_set_{st.session_state['save_n']}",
    )
else:
    st.sidebar.caption("Astuce : `pip install streamlit-js-eval` pour mémoriser vos actifs entre les visites.")

selected = [w["label"] for w in watchlist]

period_label = st.sidebar.selectbox("Période", list(PERIODS.keys()), index=3)
today = date.today()
if PERIODS[period_label] is None:
    start_date = st.sidebar.date_input("Date de début", today - timedelta(days=365), max_value=today)
    end_date = st.sidebar.date_input("Date de fin", today, max_value=today)
else:
    start_date = today - timedelta(days=PERIODS[period_label])
    end_date = today

currency = st.sidebar.radio("Devise", ["USD ($)", "EUR (€)"], horizontal=True)
log_scale = st.sidebar.checkbox(
    "Échelle logarithmique",
    value=False,
    help="Appliquée aux deux graphiques. Utile pour lire des actifs de prix très différents.",
)
if st.sidebar.button("🔄 Rafraîchir les données"):
    # Le clic relance déjà le script : il suffit de vider le cache,
    # ce qui évite st.rerun() (absent des anciennes versions de Streamlit).
    st.cache_data.clear()

# ----------------------------------------------------------------------------
# Corps de l'application
# ----------------------------------------------------------------------------
st.title("📈 Comparateur de cours")
st.caption("Comparez l'évolution des cours dans le temps. Source : Yahoo Finance.")

if not selected:
    st.info("Ajoutez au moins un actif avec la recherche de la barre latérale.")
    st.stop()
if start_date >= end_date:
    st.error("La date de début doit précéder la date de fin.")
    st.stop()

tickers = [w["ticker"] for w in watchlist]
ticker_to_name = {w["ticker"]: w["label"] for w in watchlist}
is_crypto = {w["label"]: w["crypto"] for w in watchlist}

to_download = tuple(tickers + (["EURUSD=X"] if currency.startswith("EUR") else []))

with st.spinner("Chargement des données…"):
    raw, errors = load_prices(to_download, start_date, end_date)

for t, msg in errors.items():
    st.warning(f"Échec du téléchargement de {ticker_to_name.get(t, t)} : {msg}")

if errors:
    st.caption(
        "Si l'erreur mentionne « No timezone found » ou « delisted », mettez à jour yfinance : "
        "`pip install -U yfinance`, puis redémarrez l'application."
    )

if raw.empty:
    st.error("Aucune donnée disponible pour cette sélection.")
    st.stop()

# Conversion en euros si demandé
if currency.startswith("EUR"):
    if "EURUSD=X" not in raw.columns:
        st.error("Taux EUR/USD indisponible : repassez en USD ou réessayez plus tard.")
        st.stop()
    fx = raw["EURUSD=X"].ffill()
    prices_raw = raw[[t for t in tickers if t in raw.columns]].div(fx, axis=0)
    symbol = "€"
else:
    prices_raw = raw[[t for t in tickers if t in raw.columns]]
    symbol = "$"

prices_raw = prices_raw.rename(columns=ticker_to_name)
missing = [a for a in selected if a not in prices_raw.columns or prices_raw[a].dropna().empty]
if missing:
    st.warning(f"Pas de données pour : {', '.join(missing)}")
    prices_raw = prices_raw.drop(columns=[m for m in missing if m in prices_raw.columns])
    if prices_raw.empty:
        st.stop()

# Les cryptos cotent 7j/7, les métaux 5j/7 : on aligne sur toutes les dates
# (report du dernier cours connu) et on démarre à la première date commune.
prices = prices_raw.ffill().dropna()
if prices.empty:
    st.error("Les actifs sélectionnés n'ont pas de dates communes sur cette période.")
    st.stop()

# ----------------------------------------------------------------------------
# Graphiques : prix (par défaut) puis performance base 100
# ----------------------------------------------------------------------------
def make_line_chart(df: pd.DataFrame, y_title: str, height: int = 480, rangeslider: bool = False):
    fig = px.line(df, labels={"value": y_title, "index": "Date", "variable": "Actif"})
    fig.update_layout(
        hovermode="x unified",
        legend_title_text="",
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    if log_scale:
        fig.update_yaxes(type="log")
    fig.update_xaxes(rangeslider_visible=rangeslider)
    return fig


st.subheader(f"💰 Évolution des prix ({symbol})")
st.plotly_chart(make_line_chart(prices, f"Prix ({symbol})", rangeslider=True), use_container_width=True)
if len(prices.columns) > 1 and not log_scale:
    st.caption(
        "Les prix étant très différents (ex. BTC vs argent), activez l'échelle logarithmique "
        "ou consultez le graphique de performance ci-dessous."
    )

st.subheader("📊 Performance comparée (base 100)")
performance = prices / prices.iloc[0] * 100
st.plotly_chart(make_line_chart(performance, "Performance (base 100)"), use_container_width=True)
st.caption(f"Base 100 au {prices.index[0]:%d/%m/%Y}, première date où tous les actifs ont un cours.")

# ----------------------------------------------------------------------------
# Indicateurs clés
# ----------------------------------------------------------------------------
st.subheader("Indicateurs sur la période")

rows = []
for asset in prices.columns:
    s_all = prices_raw[asset].dropna()
    s = s_all[s_all.index >= prices.index[0]]
    returns = s.pct_change().dropna()
    factor = annualization_factor(is_crypto[asset])
    rows.append(
        {
            "Actif": asset,
            f"Prix début ({symbol})": s.iloc[0],
            f"Prix fin ({symbol})": s.iloc[-1],
            "Performance": s.iloc[-1] / s.iloc[0] - 1,
            "Plus haut": s.max(),
            "Plus bas": s.min(),
            "Volatilité annualisée": returns.std() * np.sqrt(factor),
            "Drawdown max": max_drawdown(s),
        }
    )
stats = pd.DataFrame(rows).set_index("Actif")

# Cartes de synthèse
cols = st.columns(len(stats))
for col, (asset, row) in zip(cols, stats.iterrows()):
    col.metric(
        asset,
        f"{row[f'Prix fin ({symbol})']:,.2f} {symbol}",
        f"{row['Performance'] * 100:+.1f} %",
    )

st.dataframe(
    stats.style.format(
        {
            f"Prix début ({symbol})": "{:,.2f}",
            f"Prix fin ({symbol})": "{:,.2f}",
            "Plus haut": "{:,.2f}",
            "Plus bas": "{:,.2f}",
            "Performance": "{:+.1%}",
            "Volatilité annualisée": "{:.1%}",
            "Drawdown max": "{:.1%}",
        }
    ),
    use_container_width=True,
)

# ----------------------------------------------------------------------------
# Corrélations
# ----------------------------------------------------------------------------
if len(prices.columns) > 1:
    st.subheader("Corrélation des rendements hebdomadaires")
    weekly_returns = prices.resample("W").last().pct_change().dropna()
    if len(weekly_returns) >= 3:
        corr = weekly_returns.corr()
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu",
            zmin=-1,
            zmax=1,
            aspect="auto",
        )
        fig_corr.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Période trop courte pour calculer des corrélations hebdomadaires.")

# ----------------------------------------------------------------------------
# Données brutes + export
# ----------------------------------------------------------------------------
with st.expander("Voir / télécharger les données"):
    st.dataframe(prices.style.format("{:,.2f}"), use_container_width=True)
    st.download_button(
        "⬇️ Télécharger en CSV",
        data=prices.to_csv().encode("utf-8"),
        file_name="cours_comparaison.csv",
        mime="text/csv",
    )

st.caption("Données à titre informatif uniquement — ceci ne constitue pas un conseil en investissement.")
