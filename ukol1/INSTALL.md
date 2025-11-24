## Install dependencies with uv

Make sure you have [`uv`](https://github.com/astral-sh/uv) available, then install the Wikipedia client dependency:

```bash
uv pip install wikipedia
```

Set `OPENAI_MODEL` in `.env` (or your shell), then run the script with the same environment so it picks up the installed package and model:

```bash
uv run python main-wikipedia.py "Give me a quick summary of the James Webb Space Telescope."
```

Example `.env` entries:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```
