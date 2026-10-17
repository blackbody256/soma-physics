"""Route generation between local Ollama Gemma and hosted Gemma on Gemini API."""

import json
import os
from types import SimpleNamespace

import ollama

from config import CHAT_MODEL, OLLAMA_URL

LOCAL = "local"
GEMMA_API = "gemma_api"
GEMMA_API_MODEL = "gemma-4-26b-a4b-it"

_ollama = ollama.Client(host=OLLAMA_URL)
_genai = None


def gemma_api_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _gemini_client():
    global _genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemma API mode is unavailable. Set GEMINI_API_KEY on the app server.")
    if _genai is None:
        from google import genai

        _genai = genai.Client(api_key=api_key)
    return _genai


def _gemini_contents(messages, types):
    contents = []
    system_parts = []
    for message in messages:
        role = message.get("role", "user")
        if role == "system":
            system_parts.append(str(message.get("content", "")))
            continue

        parts = []
        content = str(message.get("content", ""))
        if content:
            parts.append(types.Part.from_text(text=content))
        for image in message.get("images", []):
            parts.append(types.Part.from_bytes(data=image, mime_type="image/jpeg"))
        for call in message.get("tool_calls", []):
            fn = call.function
            parts.append(types.Part.from_function_call(name=fn.name, args=fn.arguments or {}))

        if role == "tool":
            parts = [
                types.Part.from_function_response(
                    name=message.get("tool_name", "calculate"),
                    response={"result": content},
                )
            ]
            role = "user"
        else:
            role = "model" if role == "assistant" else "user"
        contents.append(types.Content(role=role, parts=parts))

    return contents, "\n\n".join(system_parts) or None


def _gemma_api_chat(**kwargs):
    from google.genai import types

    messages = kwargs.pop("messages", [])
    schema = kwargs.pop("format", None)
    ollama_tools = kwargs.pop("tools", None)
    options = kwargs.pop("options", {}) or {}
    kwargs.pop("keep_alive", None)
    think = kwargs.pop("think", None)
    # The selected API model is fixed to hosted Gemma 4 26B A4B.
    kwargs.pop("model", None)

    contents, system_instruction = _gemini_contents(messages, types)
    config = {
        key: options[key]
        for key in ("temperature", "top_p", "top_k", "num_predict")
        if key in options
    }
    if "num_predict" in config:
        config["max_output_tokens"] = config.pop("num_predict")
    if think is not None:
        config["thinking_config"] = types.ThinkingConfig(
            thinking_level="high" if think else "minimal"
        )
    if schema:
        schema_instruction = (
            "Return only a valid JSON object matching this schema. Do not wrap it in Markdown: "
            + json.dumps(schema, ensure_ascii=False)
        )
        system_instruction = "\n\n".join(filter(None, (system_instruction, schema_instruction)))
    if system_instruction:
        config["system_instruction"] = system_instruction

    if ollama_tools:
        config["tools"] = [
            types.Tool(
                function_declarations=[
                    {
                        "name": "calculate",
                        "description": (
                            "Safely evaluate arithmetic for physics calculations. "
                            "Supports numbers, + - * / **, parentheses, pi, sqrt, sin, cos, tan and log10. "
                            "Trigonometric inputs are degrees."
                        ),
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "expression": {
                                    "type": "STRING",
                                    "description": "Arithmetic expression, for example 200 / 0.05",
                                }
                            },
                            "required": ["expression"],
                        },
                    }
                ]
            )
        ]

    response = _gemini_client().models.generate_content(
        model=GEMMA_API_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(**config),
    )
    tool_calls = [
        SimpleNamespace(
            function=SimpleNamespace(name=call.name, arguments=call.args or {})
        )
        for call in (response.function_calls or [])
    ]
    return SimpleNamespace(
        message=SimpleNamespace(content=response.text or "", tool_calls=tool_calls)
    )


def chat(provider=LOCAL, **kwargs):
    if provider == LOCAL:
        kwargs.setdefault("model", CHAT_MODEL)
        return _ollama.chat(**kwargs)
    if provider == GEMMA_API:
        return _gemma_api_chat(**kwargs)
    raise ValueError("Unknown model provider.")
