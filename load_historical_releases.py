"""
Одноразовий (або нечастий, наприклад раз на місяць) скрипт.

Порядок дій:
1. Спочатку зібрати історичні дані:
   python collectors/collect_releases_by_genre.py
   -> це створить файл releases_by_genre_year.csv (займе кілька десятків хвилин,
      бо Store Search API має обмеження швидкості запитів)

2. Потім завантажити цей CSV у базу:
   python load_historical_releases.py

Результат: таблиця releases_by_genre_year у db/steam_analytics.db заповнена
реальними історичними лічильниками "жанр × рік" за 2015–2026.
Щотижневий автозапуск (run_pipeline.py) цю таблицю більше НЕ чіпає,
тож дані тут накопичуються, а не затираються.
"""
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db" / "steam_analytics.db"
CSV_PATH = BASE_DIR / "releases_by_genre_year.csv"


def main() -> None:
    if not CSV_PATH.exists():
        print(f"Не знайдено {CSV_PATH}.")
        print("Спочатку запусти: python collectors/collect_releases_by_genre.py")
        return

    df = pd.read_csv(CSV_PATH)

    conn = sqlite3.connect(DB_PATH)
    try:
        with open(BASE_DIR / "db" / "schema.sql", encoding="utf-8") as f:
            conn.executescript(f.read())  # створює таблиці, якщо бази ще не було

        for _, row in df.iterrows():
            conn.execute(
                """
                INSERT INTO releases_by_genre_year (release_year, genre, game_count, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(release_year, genre) DO UPDATE SET
                    game_count = excluded.game_count,
                    updated_at = excluded.updated_at
                """,
                (int(row["release_year"]), row["genre"], int(row["game_count"])),
            )
        conn.commit()
        print(f"Готово: {len(df)} рядків (жанр × рік) завантажено в базу.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
