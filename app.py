import streamlit as st
import requests
from urllib.parse import quote
from duckduckgo_search import DDGS

# ─── CREDENTIALS ─────────────────────────────────────────────────────────────
TMDB_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyOGIwZTc0NjM1MTkzOGIwZGUwNjNkMjM0ZjA4ZTY4ZCIsIm5iZiI6MTc3NzIzMDYyMS40MzcsInN1YiI6IjY5ZWU2MzFkMjkyYjY3NGRlZGI0ZjRkNSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.ZWSK3OoiF1-JBBt2qfLws3x-x4zbZ81HXcWzA2iH3Mg"

SITES = {
    "HDRezka":  {"domain": "hdrezka.ag",  "emoji": "🎥"},
    "Kinogo":   {"domain": "kinogo.org",   "emoji": "🎬"},
}

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pencari Film Rusia",
    page_icon="🎬",
    layout="centered",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #f7f6f2; }
    .result-card {
        background: #f9f8f5;
        border: 1px solid #d4d1ca;
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .movie-title    { font-size: 20px; font-weight: 700; color: #28251d; }
    .movie-ru-title { font-size: 16px; color: #01696f; font-weight: 600; margin-top: 4px; }
    .movie-meta     { font-size: 13px; color: #7a7974; margin-top: 6px; }
    .movie-overview { font-size: 14px; color: #28251d; margin-top: 10px; line-height: 1.5; }
    .sites-label    { font-size: 13px; color: #7a7974; margin-top: 14px; margin-bottom: 6px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; }
</style>
""", unsafe_allow_html=True)


# ─── TMDB ─────────────────────────────────────────────────────────────────────
def search_tmdb(title: str):
    headers = {"Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"}
    r = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        headers=headers,
        params={"query": title, "language": "en-US", "page": 1},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("results", [])

def get_russian_details(movie_id: int):
    headers = {"Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"}
    r = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        headers=headers,
        params={"language": "ru-RU"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("title", ""), data.get("overview", "")


# ─── DDG SEARCH PER SITE ──────────────────────────────────────────────────────
def find_on_site(ru_title: str, year: str, domain: str):
    """
    Search DuckDuckGo for site:domain "ru_title" year
    and return first valid movie page URL, or None.
    """
    ddg_query = f'site:{domain} "{ru_title}" {year}'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(ddg_query, max_results=5))
        skip_patterns = ["/search", "/page/", "/tag/", "/category/", "/genre/", "?", "#"]
        for r in results:
            url = r.get("href", "")
            if domain in url and not any(p in url for p in skip_patterns):
                return url
        return None
    except Exception:
        return None


# ─── UI ───────────────────────────────────────────────────────────────────────
st.markdown("## 🎬 Pencari Film Rusia")
st.markdown("Ketik judul film dalam bahasa Inggris — kami akan mencari judul resmi Rusianya dan menemukan tautan langsung di HDRezka dan Kinogo.")
st.markdown("---")

query = st.text_input(
    "Judul Film (Bahasa Inggris)",
    placeholder="contoh: Inception, Interstellar, The Dark Knight..."
)

if query:
    with st.spinner("Mencari di TMDb..."):
        try:
            results = search_tmdb(query)
        except Exception as e:
            st.error(f"Kesalahan TMDb: {e}")
            st.stop()

    if not results:
        st.warning("Film tidak ditemukan. Coba judul yang berbeda.")
        st.stop()

    # Take only top 3 TMDb results
    st.markdown(f"**Ditemukan {len(results)} hasil. Menampilkan 3 teratas:**")
    st.markdown("")

    for movie in results[:3]:
        movie_id = movie["id"]
        en_title = movie["title"]
        year     = movie.get("release_date", "")[:4] or ""
        rating   = movie.get("vote_average", 0)

        try:
            ru_title, ru_overview = get_russian_details(movie_id)
        except Exception:
            ru_title, ru_overview = en_title, ""

        # Search each site via DuckDuckGo
        site_links = {}
        for site_name, site_info in SITES.items():
            with st.spinner(f"Mencari di {site_name}..."):
                url = find_on_site(ru_title, year, site_info["domain"])
                site_links[site_name] = (url, site_info["emoji"])

        # Render card
        st.markdown(f"""
<div class="result-card">
    <div class="movie-title">{en_title} ({year})</div>
    <div class="movie-ru-title">🇷🇺 {ru_title}</div>
    <div class="movie-meta">⭐ {rating:.1f} / 10</div>
    {"<div class='movie-overview'>" + ru_overview[:220] + ("..." if len(ru_overview) > 220 else "") + "</div>" if ru_overview else ""}
    <div class="sites-label">Tonton di</div>
</div>
""", unsafe_allow_html=True)

        # Buttons for each site
        cols = st.columns(len(SITES))
        for col, (site_name, (url, emoji)) in zip(cols, site_links.items()):
            with col:
                if url:
                    st.link_button(f"{emoji} {site_name}", url=url, use_container_width=True)
                else:
                    fallback = f"https://{SITES[site_name]['domain']}/search/{quote(ru_title)}"
                    st.link_button(f"🔍 Cari di {site_name}", url=fallback, use_container_width=True)

        st.markdown("")
