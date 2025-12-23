"""
LangGraph agent replicující chování n8n workflow pro "enthusiastic movie assistant".
"""

import os
from typing import Annotated, List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tools import (
    postgres_healthcheck,
    postgres_select_reviews,
    postgres_upsert_review,
    tavily_search,
)

SYSTEM_MESSAGE = """You are an enthusiastic movie assistant. Follow these rules:
1) If the user did not mention a movie title, ask exactly: "Jaký film tě zajímá?"
2) If a movie is provided, give a short intro with description, genre, director, and year.
3) You may call tavily_search to refine facts about the movie.
4) Suggest your own rating 1-10 and keep it internally as agent_rating (do not ask the user to store it).
5) Ask the user for their rating 1-10 plus a short explanation.
6) If the user disagrees AND provides their own rating (e.g., 'dal bych tomu 9 protože...'), then:
   - Extract movie_name, rating (int 1-10), and rating_reason (their explanation).
   - Call postgres_upsert_review(movie_name, rating, rating_reason) to store it.
   - On success, confirm that the rating was saved.
7) Optional: postgres_select_reviews is available to check stored ratings (not required every time).
Respond in Czech. Be concise and friendly."""

TOOLS = [tavily_search, postgres_select_reviews, postgres_upsert_review]
TOOLS = [tavily_search, postgres_select_reviews, postgres_upsert_review, postgres_healthcheck]


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    movie_name: Optional[str]
    agent_rating: Optional[int]


def _make_model() -> ChatOpenAI:
    load_dotenv()
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model_name, temperature=0.2)


def _agent_node(state: AgentState):
    llm = _make_model().bind_tools(TOOLS)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def _should_continue(state: AgentState):
    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", None)
    if tool_calls:
        return "tools"
    return "end"


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", _agent_node)
    workflow.add_node("tools", ToolNode(TOOLS))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", "end": END},
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def initial_messages(system_message: str = SYSTEM_MESSAGE) -> List[BaseMessage]:
    from langchain_core.messages import SystemMessage

    return [SystemMessage(content=system_message)]


def last_ai_message(messages: List[BaseMessage]) -> Optional[AIMessage]:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None
