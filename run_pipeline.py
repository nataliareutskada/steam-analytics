"""
Головний скрипт пайплайну.

Порядок роботи:
1. Створює базу (якщо ще не існує) за схемою db/schema.sql
2. Запускає всі колектори
3. Робить upsert зібраних даних у відповідні таблиці
4. Перераховує агрегати releases_by_genre_year
5. Пише запис у pipeline_runs для діагностики

Запуск локально:  python run_pipeline.py
Запуск в CI:       та сама команда, викликається з GitHub Actions (див. .github/workflows/update_data.yml)
"""
import sqlite3
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db" / "steam_analytics.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

sys.path.append(str(BASE_DIR / "collectors"))


def init_db(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())


def upsert_games_from_steamspy(conn: sqlite3.Connection, df) -> int:
    count = 0
    for _, row in df.iterrows():
        conn.execute(
            """
            INSERT INTO games (app_id, title, developer, publisher, genres, price_usd, source, last_updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'steamspy', ?)
            ON CONFLICT(app_id) DO UPDATE SET
                title=excluded.title,
                developer=excluded.developer,
                publisher=excluded.publisher,
                genres=excluded.genres,
                price_usd=excluded.price_usd,
                last_updated_at=excluded.last_updated_at
            """,
            (
                row["app_id"], row["title"], row.get("developer"), row.get("publisher"),
                row.get("genres"), row.get("price_usd"), datetime.now(timezone.utc).isoformat(),
            ),
        )
        count += 1
    return count


def insert_player_snapshots(conn: sqlite3.Connection, df) -> int:
    count = 0
    for _, row in df.iterrows():
        if row["players_online"] is None:
            continue
        conn.execute(
            "INSERT INTO player_snapshots (app_id, players_online, collected_at) VALUES (?, ?, ?)",
            (row["app_id"], row["players_online"], row["collected_at"]),
        )
        count += 1
    return count


def insert_price_snapshots(conn: sqlite3.Connection, df) -> int:
    """Записує ціну кожної гри з поточного знімку SteamSpy — так з часом накопичується історія цін."""
    count = 0
    collected_at = datetime.now(timezone.utc).isoformat()
    for _, row in df.iterrows():
        price = row.get("price_usd")
        conn.execute(
            "INSERT INTO price_snapshots (app_id, price_usd, is_free, collected_at) VALUES (?, ?, ?, ?)",
            (row["app_id"], price, 1 if (price is None or price == 0) else 0, collected_at),
        )
        count += 1
    return count


def insert_review_snapshots(conn: sqlite3.Connection, df) -> int:
    count = 0
    for _, row in df.iterrows():
        if row.get("total_reviews") is None:
            continue
        conn.execute(
            """
            INSERT INTO review_snapshots (app_id, review_score_desc, total_positive, total_negative, total_reviews, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row["app_id"], row.get("review_score_desc"), row.get("total_positive"),
             row.get("total_negative"), row.get("total_reviews"), row["collected_at"]),
        )
        count += 1
    return count


def recompute_releases_by_genre_year(conn: sqlite3.Connection) -> None:
    """Перераховує агрегати з таблиці games (жанри зберігаються через кому)."""
    conn.execute("DELETE FROM releases_by_genre_year")
    rows = conn.execute("SELECT release_year, genres FROM games WHERE genres IS NOT NULL").fetchall()

    from collections import Counter
    counter = Counter()
    for release_year, genres in rows:
        if not release_year:
            continue
        for genre in genres.split(","):
            counter[(release_year, genre.strip())] += 1

    for (year, genre), cnt in counter.items():
        conn.execute(
            "INSERT INTO releases_by_genre_year (release_year, genre, game_count) VALUES (?, ?, ?)",
            (year, genre, cnt),
        )


def main() -> None:
    run_started = datetime.now(timezone.utc).isoformat()
    games_upserted = 0
    snapshots_added = 0
    price_snapshots_added = 0
    review_snapshots_added = 0
    status = "success"
    notes = ""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)

        # --- SteamSpy: масовий каталог (жанри/теги, видавці, ціни) ---
        try:
            import collect_steamspy_bulk
            steamspy_df = collect_steamspy_bulk.collect_all()
            games_upserted = upsert_games_from_steamspy(conn, steamspy_df)
            price_snapshots_added = insert_price_snapshots(conn, steamspy_df)
        except Exception as exc:  # noqa: BLE001 — навмисно широко, щоб один збій не зупиняв весь пайплайн
            status = "partial"
            notes += f"steamspy_failed: {exc}\n"
            traceback.print_exc()

        # --- Steam Web API: знімки кількості гравців онлайн ---
        try:
            import collect_player_counts
            tracked_ids = [row[0] for row in conn.execute("SELECT app_id FROM games LIMIT 200")]
            if not tracked_ids:
                tracked_ids = collect_player_counts.TRACKED_APP_IDS
            players_df = collect_player_counts.collect_for_app_ids(tracked_ids)
            snapshots_added = insert_player_snapshots(conn, players_df)
        except Exception as exc:  # noqa: BLE001
            status = "partial"
            notes += f"player_counts_failed: {exc}\n"
            traceback.print_exc()

        # --- Steam Appreviews: знімки рейтингів/відгуків ---
        try:
            import collect_reviews
            tracked_ids = [row[0] for row in conn.execute("SELECT app_id FROM games LIMIT 200")]
            if not tracked_ids:
                tracked_ids = [570, 730, 1172470, 1091500]
            reviews_df = collect_reviews.collect_for_app_ids(tracked_ids)
            review_snapshots_added = insert_review_snapshots(conn, reviews_df)
        except Exception as exc:  # noqa: BLE001
            status = "partial"
            notes += f"reviews_failed: {exc}\n"
            traceback.print_exc()

        # --- Store Search: релізи за жанром і роком (опційно, повільніше) ---
        # Не входить у щотижневий автозапуск (займає десятки хвилин через rate limit).
        # Запусти окремо один раз для історії: python collectors/collect_releases_by_genre.py
        # а результат підвантаж командою нижче (upsert_releases_from_csv), якщо потрібно
        # тримати ці дані саме в базі, а не лише в CSV.

        # Примітка: НЕ перераховуємо releases_by_genre_year тут щотижня —
        # ця таблиця наповнюється один раз історичними даними через
        # load_historical_releases.py і надалі не перезаписується автоматично,
        # щоб щотижневий запуск її випадково не затер порожніми значеннями.

        conn.commit()

    except Exception as exc:  # noqa: BLE001
        status = "failed"
        notes += f"pipeline_failed: {exc}\n"
        traceback.print_exc()
        conn.rollback()

    finally:
        conn.execute(
            """
            INSERT INTO pipeline_runs (run_started_at, run_finished_at, games_upserted, snapshots_added, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_started, datetime.now(timezone.utc).isoformat(), games_upserted, snapshots_added, status, notes),
        )
        conn.commit()
        conn.close()

    print(f"Пайплайн завершено зі статусом: {status}")
    print(f"Ігор оновлено: {games_upserted}, знімків онлайну: {snapshots_added}, знімків цін: {price_snapshots_added}, знімків рейтингів: {review_snapshots_added}")
    if notes:
        print("Примітки:\n" + notes)


if __name__ == "__main__":
    main()
