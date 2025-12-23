"""
Tools for Tavily search and Postgres access.
"""

import os
from time import perf_counter
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row
from tavily import TavilyClient
from langchain_core.tools import tool


def _get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set.")
    if "+psycopg" in database_url:
        database_url = database_url.replace("+psycopg", "", 1)
    return psycopg.connect(conninfo=database_url)


def _with_duration(start: float, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach duration (seconds) to tool responses for debug visibility.
    """
    payload["duration_sec"] = round(perf_counter() - start, 3)
    return payload


@tool
def tavily_search(query: str) -> Dict[str, Any]:
    """
    Vyhledávání informací o filmech. Vrací stručné výsledky s title/url/snippet.
    """
    start = perf_counter()
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return _with_duration(start, {"error": "Missing TAVILY_API_KEY."})

    client = TavilyClient(api_key=api_key)
    try:
        resp = client.search(query=query, max_results=3)
    except Exception as exc:
        return _with_duration(start, {"error": f"Tavily error: {exc}"})

    results = resp.get("results", [])
    trimmed = [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "snippet": item.get("snippet"),
        }
        for item in results
    ]
    return _with_duration(start, {"results": trimmed})


@tool
def postgres_select_reviews() -> Dict[str, Any]:
    """
    Načti všechny uložené filmové ratingy z tabulky movie_reviews (včetně rating_reason).
    """
    start = perf_counter()
    with _get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT movie_name, rating, rating_reason, updated_at FROM public.movie_reviews "
            "ORDER BY updated_at DESC, movie_name ASC;"
        )
        rows = cur.fetchall()
    return _with_duration(start, {"rows": rows})


@tool
def postgres_upsert_review(movie_name: str, rating: int, rating_reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Ulož nebo aktualizuj rating pro film spolu s textovým odůvodněním. rating musí být 1-10.
    """
    start = perf_counter()
    if not isinstance(rating, int):
        return _with_duration(start, {"error": "Rating musí být celé číslo 1-10."})
    if rating < 1 or rating > 10:
        return _with_duration(start, {"error": "Rating musí být 1-10."})

    reason = "" if rating_reason is None else str(rating_reason)

    with _get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO public.movie_reviews (movie_name, rating, rating_reason)
            VALUES (%s, %s, %s)
            ON CONFLICT (movie_name)
            DO UPDATE SET
              rating = EXCLUDED.rating,
              rating_reason = EXCLUDED.rating_reason,
              updated_at = NOW()
            RETURNING movie_name, rating, rating_reason, updated_at;
            """,
            (movie_name, rating, reason),
        )
        saved = cur.fetchone()
        conn.commit()
    return _with_duration(start, {"ok": True, "saved": saved})


def run_postgres_healthcheck() -> Dict[str, Any]:
    """
    Non-tool helper for checking DB connectivity.
    """
    start = perf_counter()
    try:
        with _get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return _with_duration(start, {"ok": True})
    except Exception as exc:
        return _with_duration(start, {"ok": False, "error": str(exc)})


@tool
def postgres_healthcheck() -> Dict[str, Any]:
    """
    Ověř, že Postgres běží (např. lokálně v Podmanu) a přijímá připojení.
    """
    return run_postgres_healthcheck()
