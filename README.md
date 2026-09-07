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

