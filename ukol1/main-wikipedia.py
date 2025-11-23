import json
import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env if present
load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else OpenAI()


def search_wikipedia(topic: str, sentences: int = 2):
    """Fetch a short summary for the topic from Wikipedia."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(topic)}"
    print(f"[tool] calling wikipedia: {url}")
    resp = requests.get(url, headers={"Accept": "application/json"}, timeout=10)

    if resp.status_code != 200:
        print(f"[tool] wikipedia error status={resp.status_code}")
        return {"topic": topic, "error": f"status {resp.status_code}"}

    data = resp.json()
    print(f"[tool] wikipedia title={data.get('title')!r}")
    return {
        "topic": topic,
        "title": data.get("title"),
        "extract": data.get("extract"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        "sentences": sentences,
    }


tools = [
    {
        "type": "function",
        "function": {
            "name": "search_wikipedia",
            "description": "Look up a topic on Wikipedia and return a short summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to look up, e.g. 'Alan Turing'.",
                    },
                    "sentences": {
                        "type": "integer",
                        "description": "Number of sentences to request (used as a hint for brevity).",
                        "default": 2,
                    },
                },
                "required": ["topic"],
            },
        },
    }
]

available_functions = {"search_wikipedia": search_wikipedia}


def run_with_tools(prompt: str, model: str = "gpt-4o-mini"):
    messages = [
        {"role": "system", "content": "You are a helpful research assistant."},
        {"role": "user", "content": prompt},
    ]

    print(f"[client] sending first request to {model!r} with prompt: {prompt!r}")
    first = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    first_message = first.choices[0].message
    print(f"[client] first response content: {first_message.content!r}")
    print(f"[client] tool calls returned: {first_message.tool_calls}")
    if not first_message.tool_calls:
        return first_message

    # Execute each requested tool call and append results.
    for tool_call in first_message.tool_calls:
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments or "{}")
        print(f"[client] executing tool: {fn_name}({fn_args})")
        fn = available_functions[fn_name]
        tool_result = fn(**fn_args)
        print(f"[client] tool result: {tool_result}")

        messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": fn_name,
                            "arguments": json.dumps(fn_args),
                        },
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": json.dumps(tool_result),
            }
        )

    second = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    second_message = second.choices[0].message
    print(f"[client] second response content: {second_message.content!r}")
    print(f"[client] second response tool calls: {second_message.tool_calls}")
    return second_message


if __name__ == "__main__":
    answer = run_with_tools("Give me a quick summary of the James Webb Space Telescope.")
    print("--- Final answer ---")
    print(answer)
