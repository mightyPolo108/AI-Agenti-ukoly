# LangGraph Movie Assistant (n8n workflow replika)

CLI agent v Pythonu, který replikuje chování exportovaného n8n workflow: chat trigger → OpenAI chat model → buffer memory → Tavily search → Postgres select/upsert. Agent je „enthusiastic movie assistant“ s českými instrukcemi.

## Požadavky
- Python 3.10+
- Závislosti: `pip install -r requirements.txt` (nebo `uv pip install -r requirements.txt` při použití UV)
- Postgres dostupný přes `DATABASE_URL` (psycopg driver)
- API klíče v `.env` (viz `.env.example`)

## Nastavení
1) Zkopíruj `.env.example` do `.env` a doplň hodnoty:
   ```
   OPENAI_API_KEY=...
   OPENAI_MODEL=gpt-4.1-mini
   TAVILY_API_KEY=...
   DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
   ```
2) Instaluj balíčky:
   ```
   pip install -r requirements.txt
   # nebo s uv:
   uv pip install -r requirements.txt
   ```
3) Spusť migraci:
   ```
   psql "$DATABASE_URL" -f migrations/001_create_movie_reviews.sql
   ```

## Spuštění (CLI chat)
```
python app.py
```
Příkazy pro ukončení: `exit`, `quit`, nebo Ctrl+D/Ctrl+C.

Paměť: posledních 10 zpráv (ekvivalent MemoryBufferWindow). Agent automaticky volá nástroje (Tavily / Postgres) podle zadání.

## Testovací scénáře
1) Uživatel: „Ahoj“  
   Agent: „Jaký film tě zajímá?“
2) Uživatel: „Zajímá mě Inception“  
   Agent: krátký úvod (popis/žánr/režisér/rok), navrhne svůj rating 1–10, vyzve k ratingu uživatele.
3) Uživatel: „Já bych tomu dal 9 protože…“ (film z kontextu)  
   Agent: uloží rating do DB přes `postgres_upsert_review` a potvrdí uložení.

## Struktura
```
.
├─ app.py                  # CLI chat rozhraní
├─ agent_graph.py          # LangGraph stavový graf a systémový prompt
├─ tools.py                # Tavily + Postgres tools
├─ migrations/001_create_movie_reviews.sql
├─ requirements.txt
├─ .env.example
└─ README.md
```

## Poznámky k implementaci
- Nástroje:
  - `tavily_search(query)` používá Tavily API (max 3 výsledky).
  - `postgres_select_reviews()` načítá uložené ratingy.
  - `postgres_upsert_review(movie_name, rating)` validuje 1–10 a dělá upsert na unikátní `movie_name`.
  - `postgres_healthcheck()` ověří, že Postgres je dostupný (užitečné pro lokální Podman).
- LLM: OpenAI chat model (`OPENAI_MODEL`, default `gpt-4.1-mini`) s teplotou 0.2.
- Graf: agent node (LLM + tool calls) → tool node → agent; končí, když není potřeba tool.
