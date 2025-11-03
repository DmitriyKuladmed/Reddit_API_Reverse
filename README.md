# Reddit_API_Reverse (compliant)

Этот проект предоставляет безопасный способ получить посты из сабреддита `/r/technology` через официальный Reddit API (OAuth2), а также локальный учебный стенд для демонстрации навыков реверс‑инжиниринга без нарушения правил.

## Структура
- `src/reddit_api_client.py` — минимальный клиент OAuth2 и листинг постов
- `src/cli.py` — CLI-утилита для выборки постов и вывода в JSON/JSONL
- `src/lab_server.py` — локальный Flask API с псевдо‑защитами (rate limit, токен)
- `src/lab_static/` — учебный веб‑клиент с лёгкой обфускацией
- `requirements.txt` — зависимости

## Быстрый старт (официальный Reddit API)
1) Создайте Reddit App и получите `client_id` и `client_secret`.
2) Виртуальное окружение и зависимости:
```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```
3) Конфигурация через .env (Pydantic Settings):
- Создайте файл `.env` в корне проекта со значениями:
```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=your-app-name/1.0 (contact@example.com)
```
- Переменные также могут быть заданы через окружение — приоритет у env.
4) Пример запуска:
```
python -m src.cli technology --listing new --max-items 50 --output jsonl
```

## Локальный учебный стенд (реверс‑инжиниринг)
1) Запуск стенда:
```
python -m src.lab_server
```
Откройте `http://127.0.0.1:5000/` и нажмите «Fetch posts».

2) Суть стенда:
- `POST /api/token` выдаёт токен, привязанный к `User-Agent`.
- `GET /api/posts` требует заголовок `Authorization: Bearer <token>` и уважает rate limit (429 + Retry-After).
- Веб‑клиент (`lab_static/app.js`) слегка обфусцирован.

## Отчёт (суммарно, пункты 1–6)

### Reddit (официальный API, без реверса/обхода)
- **1) Эндпоинты**: `https://oauth.reddit.com/r/technology/{hot|new|top}`; параметры: `limit<=100`, `after`/`before`, для `top` — `t` (`hour|day|week|month|year|all`).
- **2) Авторизация**: OAuth2 `client_credentials`; токен по `POST https://www.reddit.com/api/v1/access_token` (Basic client_id:client_secret), далее `Authorization: Bearer <token>`, обязательный `User-Agent`.
- **3) Токены**: выдает Reddit; срок ~час; обновление автоматически в `src/reddit_api_client.py`.
- **4) Защиты**: rate limits (`429` + `Retry-After`), требование `User-Agent`, анти‑абьюз. Не использовать не‑документированные эндпоинты.
- **5) Легитимный трафик**: честный `User-Agent`, пагинация, кэширование, уважение `Retry-After`.
- **6) Rate limit**: экспоненциальный бэкофф, уменьшение параллелизма, батчинг.

### Локальный «Reverse Lab» (демонстрация методологии реверса)
- **1) Эндпоинт**: `GET /api/posts?subreddit=technology&limit=5` (найден через DevTools/Network при клике «Fetch posts»).
- **2) Авторизация**: `Authorization: Bearer <token>` + привязка к `User-Agent`.
- **3) Токен**: `POST /api/token` выдаёт токен; в сервере `_issue_token(user_agent)` использует учебный `_toy_hash(user_agent+":"+SECRET)`; в `lab_static/app.js` — лёгкая обфускация строк.
- **4) Защиты**: rate limit (5 запросов/10с на IP → `429` + `Retry-After`), привязка к UA, лёгкая обфускация.
- **5) Эмуляция легитимного трафика**: последовательность `POST /api/token` → `GET /api/posts` с тем же UA + соблюдение `Retry-After`.
- **6) Работа с лимитами**: пауза по `Retry-After`, снижение частоты; в JS реализован повтор, аналог легко сделать на Python.

Пример кода для стенда (Python):
```python
import requests, time
ua = "lab-reverse-client/1.0"
base = "http://127.0.0.1:5000"
h = {"User-Agent": ua}

def with_rl_retry(method, url, **kw):
    for _ in range(5):
        r = requests.request(method, url, **kw)
        if r.status_code != 429:
            return r
        time.sleep(float(r.headers.get("Retry-After", "1")))
    raise RuntimeError("rate limit")

# 1) получить токен
r = with_rl_retry("POST", f"{base}/api/token", headers=h)
r.raise_for_status()
access_token = r.json()["token"]
# 2) получить посты
h2 = {**h, "Authorization": f"Bearer {access_token}"}
r = with_rl_retry("GET", f"{base}/api/posts?subreddit=technology&limit=5", headers=h2)
r.raise_for_status()
print(r.json())
```

## Обработка Rate Limit
Клиент уважает `429` и заголовок `Retry-After`, применяет экспоненциальный бэкофф.