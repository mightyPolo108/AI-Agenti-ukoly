import argparse
import json
import os

import wikipedia
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env if present
load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")
model_env = os.environ.get("OPENAI_MODEL")
client = OpenAI(api_key=api_key) if api_key else OpenAI()


def search_wikipedia(topic: str, sentences: int = 2):
    """Fetch a short summary for the topic using the `wikipedia` PyPI package."""
    wikipedia.set_lang("en")
    print(f"[tool] calling wikipedia library for topic={topic!r} with sentences={sentences}")

    try:
        summary = wikipedia.summary(
            topic, sentences=sentences, auto_suggest=False, redirect=True
        )
        page = wikipedia.page(topic, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as exc:
        print("[tool] disambiguation error")
        return {"topic": topic, "error": "disambiguation", "options": exc.options[:5]}
    except wikipedia.exceptions.PageError:
        print("[tool] page error")
        return {"topic": topic, "error": "page not found"}
    except Exception as exc:  # pragma: no cover - catch-all for library/network issues
        print(f"[tool] wikipedia exception: {exc}")
        return {"topic": topic, "error": str(exc)}

    print(f"[tool] wikipedia title={page.title!r}")
    return {
        "topic": topic,
        "title": page.title,
        "extract": summary,
        "url": page.url,
        "sentences": sentences,
    }


TOOLS = [
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

AVAILABLE_FUNCTIONS = {"search_wikipedia": search_wikipedia}


def run_with_tools(
    prompt: str,
    tools,
    available_functions,
    model: str
    ):
    model_to_use = model or model_env
    if not model_to_use:
        raise RuntimeError("Model name not provided; set OPENAI_MODEL or pass model explicitly.")
    messages = [
        {"role": "system", "content": "You are a helpful research assistant."},
        {"role": "user", "content": prompt},
    ]
    while True:
        print(f"[client] sending request to {model_to_use!r} with prompt: {prompt!r}")
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        message = response.choices[0].message
        print(f"[client] response content: {message.content!r}")
        print(f"[client] tool calls returned: {message.tool_calls}")

        if not message.tool_calls:
            return message

        assistant_tool_call_msg = {"role": "assistant", "tool_calls": []}
        tool_messages = []

        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments or "{}")
            print(f"[client] executing tool: {fn_name}({fn_args})")
            fn = available_functions[fn_name]
            tool_result = fn(**fn_args)
            print(f"[client] tool result: {tool_result}")

            assistant_tool_call_msg["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "arguments": json.dumps(fn_args),
                    },
                }
            )

            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": json.dumps(tool_result),
                }
            )

        messages.append(assistant_tool_call_msg)
        messages.extend(tool_messages)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask the model to summarize a topic.")
    parser.add_argument(
        "prompt",
        help="Prompt to send to the model, e.g. 'Give me a quick summary of the James Webb Space Telescope.'",
    )
    args = parser.parse_args()

    answer = run_with_tools(
        prompt=args.prompt, tools=TOOLS, available_functions=AVAILABLE_FUNCTIONS
    )
    print("--- Final answer ---")
    print(answer)
