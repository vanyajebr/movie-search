import streamlit as st
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

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
    .kinogo-link    { font-size: 14px; color: #01696f; margin-top: 10px; font-weight: 500; }
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


# ─── KINOGO SCRAPER ───────────────────────────────────────────────────────────
def scrape_kinogo(ru_title: str):
    """
    Search Kinogo and return (direct_url, search_url).
    direct_url is the first result found, or None if scraping fails.
    search_url is always returned as a reliable fallback.
    """
    search_url = f"{KINOGO_BASE}/search/{quote(ru_title)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
        "Referer": KINOGO_BASE,
    }

    try:
        r = requests.get(search_url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # DLE engine standard: movie cards are in .short or .shortstory
        # Links are in h2 > a or .short-title a or .posttitle a
        selectors = [
            "article.short h2 a",
            "div.short h2 a",
            "div.shortstory h2 a",
            ".short-title a",
            ".posttitle a",
            "h2.zagolovok a",
            ".news-title a",
            "h2 a",  # broad fallback
        ]

        for selector in selectors:
            link = soup.select_one(selector)
            if link and link.get("href"):
                href = link["href"]
                if not href.startswith("http"):
                    href = KINOGO_BASE + href
                return href, search_url

        return None, search_url

    except Exception:
        return None, search_url


# ─── UI ───────────────────────────────────────────────────────────────────────
st.markdown("## 🎬 Kinogo Finder")
st.markdown("Type a movie title in English — get the official Russian title and a direct link to Kinogo.")
st.markdown("---")

query = st.text_input("Movie title (English)", placeholder="e.g. Inception, Interstellar, Home Alone...")

if query:
    with st.spinner("Searching TMDb..."):
        try:
            results = search_tmdb(query)
        except Exception as e:
            st.error(f"TMDb error: {e}")
            st.stop()

    if not results:
        st.warning("No movies found on TMDb. Try a different title.")
        st.stop()

    st.markdown(f"**Found {len(results)} result(s). Showing top 5:**")
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

        # Scrape Kinogo for direct link
        with st.spinner(f"Looking up '{ru_title}' on Kinogo..."):
            direct_url, search_url = scrape_kinogo(ru_title)

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
                st.link_button("🎬 Watch on Kinogo", url=direct_url, use_container_width=True)
            else:
                st.caption("⚠️ Direct link unavailable")
        with col2:
            st.link_button("🔍 Search on Kinogo", url=search_url, use_container_width=True)

        st.markdown("")
