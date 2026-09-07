# Steam Analytics — портфоліо-проєкт

Автоматизований збір даних про ігри Steam (жанри, релізи за роками, ціни,
кількість гравців онлайн) для аналізу в SQL і візуалізації в Tableau.

## Структура

```
steam-analytics/
├── collectors/
│   ├── collect_releases_by_genre.py   # Store Search API: кількість релізів жанр × рік
│   ├── collect_steamspy_bulk.py       # SteamSpy: каталог ігор, теги, ціни, власники
│   └── collect_player_counts.py       # Steam Web API: онлайн зараз (часовий ряд)
├── db/
│   ├── schema.sql                     # схема SQLite
│   └── steam_analytics.db             # база даних (створюється при першому запуску)
├── .github/workflows/update_data.yml  # автозапуск раз на тиждень
├── run_pipeline.py                    # головний скрипт: збір → база
└── requirements.txt
```

## Швидкий старт (локально)

```bash
pip install -r requirements.txt
python run_pipeline.py
```

Після першого запуску з'явиться `db/steam_analytics.db` — SQLite-база,
яку можна одразу підключити до Tableau (Tableau Desktop → Connect → SQLite,
може знадобитись ODBC-драйвер для SQLite).

## Автоматизація

Файл `.github/workflows/update_data.yml` запускає `run_pipeline.py` щопонеділка
й комітить оновлену базу назад у репозиторій. Щоб увімкнути:

1. Заливаєш увесь проєкт у GitHub-репозиторій
2. У Settings → Actions → General дозволяєш workflow писати в репозиторій
   (Workflow permissions → Read and write)
3. Все — далі оновлюється саме, а вручну можна запустити кнопкою
   "Run workflow" на вкладці Actions

## SQL-запити для Tableau / аналізу

Кілька прикладів для таблиці `releases_by_genre_year`:

```sql
-- Топ-5 жанрів за останній рік
SELECT genre, game_count
FROM releases_by_genre_year
WHERE release_year = 2026
ORDER BY game_count DESC
LIMIT 5;

-- Динаміка жанру Indie по роках
SELECT release_year, game_count
FROM releases_by_genre_year
WHERE genre = 'Indie'
ORDER BY release_year;
```

Для `player_snapshots` — часові ряди онлайну по грі, для heatmap пікових годин/днів.

## SQL для аналітики по видавцях (дані вже є, нового збору не треба)

```sql
-- Топ-10 видавців за кількістю ігор у каталозі
SELECT publisher, COUNT(*) AS games_count, ROUND(AVG(price_usd), 2) AS avg_price
FROM games
WHERE publisher IS NOT NULL
GROUP BY publisher
ORDER BY games_count DESC
LIMIT 10;

-- Видавці з найвищим середнім рейтингом (потребує review_snapshots)
SELECT g.publisher,
       ROUND(AVG(CAST(r.total_positive AS FLOAT) / NULLIF(r.total_reviews, 0)) * 100, 1) AS avg_positive_pct,
       COUNT(DISTINCT g.app_id) AS games_tracked
FROM games g
JOIN review_snapshots r ON r.app_id = g.app_id
WHERE g.publisher IS NOT NULL
GROUP BY g.publisher
HAVING games_tracked >= 2
ORDER BY avg_positive_pct DESC
LIMIT 10;

-- Динаміка ціни конкретної гри з часом
SELECT collected_at, price_usd
FROM price_snapshots
WHERE app_id = 570  -- підстав потрібний app_id
ORDER BY collected_at;
```

## Що можна розширити далі

- Додати `collect_releases_by_genre.py` у щотижневий запуск (зараз він
  повільний через rate limit — краще запускати окремо раз на місяць)
- Winsorize/очищення викидів у `owners_estimate` перед аналізом
- Парсинг `results_html` у Store Search для отримання не лише кількості,
  а й списку конкретних назв ігор по кожній комбінації жанр+рік
