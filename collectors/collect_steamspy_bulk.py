"""
Масовий збір каталогу ігор із SteamSpy.

Джерело: https://steamspy.com/api.php
Ендпоінт `all` віддає сторінками по ~1000 ігор, відсортованих за популярністю.
Ключ API не потрібен, але є неофіційний ліміт ~1 запит/секунду.

Примітка: цей ендпоінт НЕ містить дати виходу гри — для аналізу
"жанр × рік" використовуй collect_releases_by_genre.py, а цей скрипт
дає ширші дані про теги, власників і ціни для вже відомих ігор.
"""
import time
import requests
import pandas as pd

STEAMSPY_URL = "https://steamspy.com/api.php"
REQUEST_DELAY_SEC = 1.2

MAX_PAGES = 60  # ~60 000 ігор; збільш за потреби, але враховуй час виконання


def fetch_page(page: int) -> dict:
    params = {"request": "all", "page": page}
    resp = requests.get(STEAMSPY_URL, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def collect_all() -> pd.DataFrame:
    rows = []
    for page in range(MAX_PAGES):
        data = fetch_page(page)
        if not data:
            break  # порожня сторінка = дійшли до кінця каталогу

        for app_id, info in data.items():
            rows.append({
                "app_id": app_id,
                "title": info.get("name"),
                "developer": info.get("developer"),
                "publisher": info.get("publisher"),
                "genres": info.get("tags") and ",".join(list(info["tags"].keys())[:5]),
                "price_usd": _cents_to_usd(info.get("price")),
                "owners_estimate": info.get("owners"),
                "average_playtime_min": info.get("average_forever"),
            })

        time.sleep(REQUEST_DELAY_SEC)

    return pd.DataFrame(rows)


def _cents_to_usd(price_cents):
    if price_cents in (None, "", "0"):
        return None
    try:
        return round(int(price_cents) / 100, 2)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    df = collect_all()
    df.to_csv("steamspy_catalog.csv", index=False)
    print(f"Готово: {len(df)} ігор збережено у steamspy_catalog.csv")
