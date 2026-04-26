import streamlit as st
import requests
from urllib.parse import quote
from googlesearch import search

# ─── CREDENTIALS ─────────────────────────────────────────────────────────────
TMDB_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyOGIwZTc0NjM1MTkzOGIwZGUwNjNkMjM0ZjA4ZTY4ZCIsIm5iZiI6MTc3NzIzMDYyMS40MzcsInN1YiI6IjY5ZWU2MzFkMjkyYjY3NGRlZGI0ZjRkNSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.ZWSK3OoiF1-JBBt2qfLws3x-x4zbZ81HXcWzA2iH3Mg"
KINOGO_BASE = "https://kinogo.org"

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kinogo Finder",
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
        margin-bottom: 12px;
    }
    .movie-title    { font-size: 20px; font-weight: 700; color: #28251d; }
    .movie-ru-title { font-size: 16px; color: #01696f; font-weight: 600; margin-top: 4px; }
    .movie-meta     { font-size: 13px; color: #7a7974; margin-top: 6px; }
    .movie-overview { font-size: 14px; color: #28251d; margin-top: 10px; line-height: 1.5; }
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


# ─── GOOGLE → KINOGO ──────────────────────────────────────────────────────────
def find_kinogo_link(ru_title: str, year: str):
    """
    Use Google search with site:kinogo.org to find the direct movie page.
    Falls back to Kinogo search URL if nothing found.
    """
    search_url = f"{KINOGO_BASE}/search/{quote(ru_title)}"
    query = f'site:kinogo.org "{ru_title}" {year}'

    try:
        results = list(search(query, num_results=5, lang="ru"))
        for url in results:
            # Only return actual movie pages, not search/tag/category pages
            if (
                "kinogo.org" in url
                and "/search/" not in url
                and "/page/" not in url
                and "/tag/" not in url
                and "/category/" not in url
                and len(url.split("/")) >= 4
            ):
                return url, search_url
        return None, search_url
    except Exception:
        return None, search_url


# ─── UI ───────────────────────────────────────────────────────────────────────
st.markdown("## 🎬 Kinogo Finder")
st.markdown("Ketik judul film dalam bahasa Inggris — temukan judul resmi dalam bahasa Rusia dan tonton langsung di Kinogo.")
st.markdown("---")

query = st.text_input(
    "Judul Film (Bahasa Inggris)",
    placeholder="contoh: Inception, Interstellar, Home Alone..."
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

    st.markdown(f"**Ditemukan {len(results)} hasil. Menampilkan 5 teratas:**")
    st.markdown("")

    for movie in results[:5]:
        movie_id = movie["id"]
        en_title = movie["title"]
        year     = movie.get("release_date", "")[:4] or "?"
        rating   = movie.get("vote_average", 0)

        try:
            ru_title, ru_overview = get_russian_details(movie_id)
        except Exception:
            ru_title, ru_overview = en_title, ""

        with st.spinner(f"Mencari '{ru_title}' di Kinogo..."):
            direct_url, search_url = find_kinogo_link(ru_title, year)

        st.markdown(f"""
<div class="result-card">
    <div class="movie-title">{en_title} ({year})</div>
    <div class="movie-ru-title">🇷🇺 {ru_title}</div>
    <div class="movie-meta">⭐ {rating:.1f} / 10</div>
    {"<div class='movie-overview'>" + ru_overview[:220] + ("..." if len(ru_overview) > 220 else "") + "</div>" if ru_overview else ""}
</div>
""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if direct_url:
                st.link_button("🎬 Tonton di Kinogo", url=direct_url, use_container_width=True)
            else:
                st.caption("⚠️ Tautan langsung tidak tersedia")
        with col2:
            st.link_button("🔍 Cari di Kinogo", url=search_url, use_container_width=True)

        st.markdown("")
