"""
Tools for Tavily search and Postgres access.
"""

import os
from typing import Any, Dict, List

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


@tool
def tavily_search(query: str) -> Dict[str, Any]:
    """
    Vyhledávání informací o filmech. Vrací stručné výsledky s title/url/snippet.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"error": "Missing TAVILY_API_KEY."}

    client = TavilyClient(api_key=api_key)
    try:
        resp = client.search(query=query, max_results=3)
    except Exception as exc:
        return {"error": f"Tavily error: {exc}"}

    results = resp.get("results", [])
    trimmed = [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "snippet": item.get("snippet"),
        }
        for item in results
    ]
    return {"results": trimmed}


@tool
def postgres_select_reviews() -> List[Dict[str, Any]]:
    """
    Načti všechny uložené filmové ratingy z tabulky movie_reviews.
    """
    with _get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT movie_name, rating, updated_at FROM public.movie_reviews "
            "ORDER BY updated_at DESC, movie_name ASC;"
        )
        rows = cur.fetchall()
    return rows


@tool
def postgres_upsert_review(movie_name: str, rating: int) -> Dict[str, Any]:
    """
    Ulož nebo aktualizuj rating pro film. rating musí být 1-10.
    """
    if not isinstance(rating, int):
        return {"error": "Rating musí být celé číslo 1-10."}
    if rating < 1 or rating > 10:
        return {"error": "Rating musí být 1-10."}

    with _get_db_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO public.movie_reviews (movie_name, rating)
            VALUES (%s, %s)
            ON CONFLICT (movie_name)
            DO UPDATE SET rating = EXCLUDED.rating, updated_at = NOW()
            RETURNING movie_name, rating, updated_at;
            """,
            (movie_name, rating),
        )
        saved = cur.fetchone()
        conn.commit()
    return {"ok": True, "saved": saved}


def run_postgres_healthcheck() -> Dict[str, Any]:
    """
    Non-tool helper for checking DB connectivity.
    """
    try:
        with _get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool
def postgres_healthcheck() -> Dict[str, Any]:
    """
    Ověř, že Postgres běží (např. lokálně v Podmanu) a přijímá připojení.
    """
    return run_postgres_healthcheck()
