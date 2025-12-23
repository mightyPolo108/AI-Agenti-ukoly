"""
CLI chat rozhraní pro LangGraph movie assistant.
"""

import argparse
import sys
from typing import List

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from rich.console import Console
from rich.panel import Panel

from agent_graph import SYSTEM_MESSAGE, build_graph, initial_messages, last_ai_message
from tools import run_postgres_healthcheck

WINDOW_SIZE = 10  # ekvivalent MemoryBufferWindow


def trim_history(messages: List[BaseMessage], window: int = WINDOW_SIZE) -> List[BaseMessage]:
    """Keep system messages and the last N other messages."""
    system_msgs = [m for m in messages if m.type == "system"]
    other = [m for m in messages if m.type != "system"]
    kept = other[-window:]
    return system_msgs + kept


def run_cli(debug: bool = False) -> None:
    load_dotenv()
    console = Console()

    # Check DB availability before starting
    health = run_postgres_healthcheck()
    if not health.get("ok"):
        console.print(f"[red]DB healthcheck failed:[/red] {health.get('error')}")
        sys.exit(1)
    elif debug:
        console.print("[green]DB healthcheck passed.[/green]")

    graph = build_graph()
    messages: List[BaseMessage] = initial_messages()

    console.print("[bold green]Enthusiastic Movie Assistant[/] (např. napiš 'Ahoj' nebo 'Zajímá mě Inception')")
    console.print("Pro ukončení napiš: exit / quit / ctrl+d\n")

    while True:
        try:
            user_input = console.input("[bold blue]Ty:[/bold blue] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold yellow]Konec.[/bold yellow]")
            break

        if user_input.lower() in {"exit", "quit"}:
            console.print("[bold yellow]Konec.[/bold yellow]")
            break
        if not user_input:
            continue

        messages.append(HumanMessage(content=user_input))
        messages = trim_history(messages)

        prev_len = len(messages)
        result = graph.invoke({"messages": messages})
        messages = result["messages"]
        new_messages = messages[prev_len:]

        if debug:
            for m in new_messages:
                if m.type == "ai" and getattr(m, "tool_calls", None):
                    info_lines = []
                    for tc in m.tool_calls:
                        info_lines.append(f"{tc['name']}({tc.get('args')})")
                    console.print(Panel("\n".join(info_lines), title="Tool calls", border_style="cyan"))
                elif m.type == "tool":
                    console.print(Panel(str(m.content), title=f"Tool result: {m.name}", border_style="green"))

        ai_msg = last_ai_message(messages)
        if ai_msg:
            console.print(f"[bold magenta]Agent:[/bold magenta] {ai_msg.content}\n")
        else:
            console.print("[red]Agent nevrátil odpověď.[/red]\n")


def main():
    parser = argparse.ArgumentParser(description="CLI chat pro enthusiastic movie assistant (LangGraph).")
    parser.add_argument("--debug", action="store_true", help="Zobrazí log kroků agenta a volání nástrojů.")
    args = parser.parse_args()
    run_cli(debug=args.debug)


if __name__ == "__main__":
    sys.exit(main())
