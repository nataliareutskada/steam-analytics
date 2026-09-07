"""
Збирає підсумкові рейтинги (кількість позитивних/негативних відгуків,
словесна оцінка типу "Overwhelmingly Positive") для заданого списку ігор
через офіційний Steam Appreviews API.

Джерело: https://store.steampowered.com/appreviews/{app_id}
Не потребує ключа. Запускати регулярно (як і онлайн, і ціну) —
так з часом накопичується історія: чи росте задоволеність грою після патчів,
чи падає після спірних оновлень.
"""
import time
import requests
import pandas as pd

APPREVIEWS_URL = "https://store.steampowered.com/appreviews/{app_id}"
REQUEST_DELAY_SEC = 1.0


def fetch_review_summary(app_id: int) -> dict | None:
    url = APPREVIEWS_URL.format(app_id=app_id)
    params = {"json": 1, "language": "all", "purchase_type": "all", "num_per_page": 0}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("success") != 1:
        return None

    summary = data.get("query_summary", {})
    return {
        "review_score_desc": summary.get("review_score_desc"),   # напр. "Very Positive"
        "total_positive": summary.get("total_positive"),
        "total_negative": summary.get("total_negative"),
        "total_reviews": summary.get("total_reviews"),
    }


def collect_for_app_ids(app_ids: list[int]) -> pd.DataFrame:
    rows = []
    for app_id in app_ids:
        try:
            summary = fetch_review_summary(app_id)
        except requests.RequestException as exc:
            summary = None
            print(f"Помилка для app_id={app_id}: {exc}")

        if summary is None:
            summary = {"review_score_desc": None, "total_positive": None, "total_negative": None, "total_reviews": None}

        rows.append({
            "app_id": app_id,
            **summary,
            "collected_at": pd.Timestamp.utcnow().isoformat(),
        })
        time.sleep(REQUEST_DELAY_SEC)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    TRACKED_APP_IDS = [570, 730, 1172470, 1091500]  # той самий список, що й для онлайну
    df = collect_for_app_ids(TRACKED_APP_IDS)
    df.to_csv("review_snapshots.csv", index=False)
    print(f"Готово: {len(df)} знімків рейтингів збережено у review_snapshots.csv")
