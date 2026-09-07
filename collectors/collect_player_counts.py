"""
Збирає поточну кількість гравців онлайн для заданого списку app_id
через офіційний Steam Web API (безкоштовний, без ключа для цього методу).

Джерело: ISteamUserStats/GetNumberOfCurrentPlayers
Запускати регулярно (наприклад, щодня) — так накопичується часовий ряд
для аналізу сезонності й піків активності.
"""
import time
import requests
import pandas as pd

PLAYER_COUNT_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
REQUEST_DELAY_SEC = 1.0


def fetch_player_count(app_id: int) -> int | None:
    resp = requests.get(PLAYER_COUNT_URL, params={"appid": app_id}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", {}).get("player_count")


# Список app_id, які відстежуєш за замовчуванням (топ-ігри, конкуренти, ніша тощо).
# run_pipeline.py підміняє цей список реальними app_id з таблиці games, якщо вона не порожня.
TRACKED_APP_IDS = [
    570,      # Dota 2
    730,      # CS2
    1172470,  # Apex Legends
    1091500,  # Cyberpunk 2077
]


def collect_for_app_ids(app_ids: list[int]) -> pd.DataFrame:
    rows = []
    for app_id in app_ids:
        try:
            count = fetch_player_count(app_id)
        except requests.RequestException as exc:
            count = None
            print(f"Помилка для app_id={app_id}: {exc}")

        rows.append({
            "app_id": app_id,
            "players_online": count,
            "collected_at": pd.Timestamp.utcnow().isoformat(),
        })
        time.sleep(REQUEST_DELAY_SEC)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = collect_for_app_ids(TRACKED_APP_IDS)
    df.to_csv("player_snapshots.csv", index=False)
    print(f"Готово: {len(df)} знімків збережено у player_snapshots.csv")
