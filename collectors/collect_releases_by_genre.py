"""
Збирає список ігор Steam за комбінаціями (жанр, рік виходу)
через публічний Store Search API.

Джерело: https://store.steampowered.com/search/results
Не потребує ключа API.
"""
import time
import requests
import pandas as pd

SEARCH_URL = "https://store.steampowered.com/search/results/"

# Основні жанри Steam (tag id можна уточнити на сторінці store, тут — назви жанрів)
GENRES = [
    "Action", "Adventure", "RPG", "Strategy", "Simulation",
    "Sports", "Racing", "Indie", "Casual", "Puzzle",
]

YEARS = list(range(2015, 2027))  # налаштуй діапазон під себе

REQUEST_DELAY_SEC = 1.5  # ввічлива затримка між запитами, щоб не отримати бан по IP


def fetch_genre_year_page(genre: str, year: int, start: int = 0, count: int = 100) -> dict:
    """Один запит до Store Search API з фільтром жанру й року виходу."""
    params = {
        "query": "",
        "start": start,
        "count": count,
        "genre": genre,
        "release_date": f"{year}-01-01,{year}-12-31",
        "infinite": 1,
        "cc": "us",
        "l": "english",
    }
    resp = requests.get(SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def collect_all() -> pd.DataFrame:
    rows = []
    for year in YEARS:
        for genre in GENRES:
            start = 0
            total_for_combo = None
            while True:
                data = fetch_genre_year_page(genre, year, start=start)
                total_for_combo = data.get("total_count", 0)
                html_snippet = data.get("results_html", "")

                # Store Search повертає HTML-фрагмент; тут беремо лише total_count
                # для агрегованої кількості. Для повного списку назв ігор
                # знадобиться парсинг html_snippet (можна додати BeautifulSoup).
                rows.append({
                    "genre": genre,
                    "release_year": year,
                    "game_count": total_for_combo,
                })
                break  # рахуємо загальну кількість одним запитом, без пагінації по назвах

            time.sleep(REQUEST_DELAY_SEC)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = collect_all()
    df.to_csv("releases_by_genre_year.csv", index=False)
    print(f"Готово: {len(df)} рядків (жанр × рік) збережено у releases_by_genre_year.csv")
