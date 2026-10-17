import json
import re

import ollama

from config import (
    CALC_OPTIONS,
    CHAT_MODEL,
    KEEP_ALIVE,
    OPTIONS,
    SELF_CHECK,
    STRICT_OPTIONS,
    USE_THINKING,
)
from prompts import (
    ACTIVITY_PROMPT,
    ACTIVITY_SCHEMA,
    ANSWER_SCHEMA,
    CHECK_PROMPT,
    CHECK_SCHEMA,
    FEW_SHOT,
    SOLVER_PROMPT,
    SYSTEM_PROMPT,
)
from retrieve import Index
from model_router import GEMMA_API, LOCAL, chat as route_chat
from tools import calculate

index = Index()

NO_CONTEXT = "NO MATCHING SYLLABUS CONTENT. Tell the learner kindly that this is outside the syllabus."


def chat(provider=LOCAL, **kwargs):
    kwargs.setdefault("model", CHAT_MODEL)
    kwargs.setdefault("keep_alive", KEEP_ALIVE)
    if provider == GEMMA_API:
        return route_chat(provider=provider, **kwargs)
    try:
        return route_chat(provider=provider, **kwargs)
    except ollama.ResponseError as err:
        if kwargs.get("think") and "think" in str(err).lower():
            kwargs.pop("think", None)
            return route_chat(provider=provider, **kwargs)
        raise


def parse_json(text, fallback):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {**fallback, "answer": text or ""}


def format_context(chunks):
    blocks = []
    for c in chunks:
        label = c["topic"] + (f", {c['subtopic']}" if c["subtopic"] else "")
        blocks.append(f"[{label}]\n{c['text']}")
    return "\n\n".join(blocks)


def is_calculation(question: str) -> bool:
    return bool(re.search(r"\d", question))


def solve_with_tools(question, context, provider=LOCAL):
    messages = [
        {"role": "system", "content": SOLVER_PROMPT},
        {"role": "user", "content": f"SYLLABUS CONTEXT:\n{context}\n\nQUESTION: {question}"},
    ]
    results = []
    for _ in range(5):
        msg = chat(provider=provider, messages=messages, tools=[calculate], think=USE_THINKING, options=CALC_OPTIONS).message
        if not msg.tool_calls:
            return msg.content or "", results
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
        for call in msg.tool_calls:
            args = call.function.arguments or {}
            expr = str(args.get("expression", ""))
            out = calculate(expr) if call.function.name == "calculate" else "error: unknown tool"
            results.append(f"{expr} = {out}")
            messages.append({"role": "tool", "content": out, "tool_name": call.function.name})
    return "", results


def self_check(question, data, provider=LOCAL):
    steps = "\n".join(data.get("worked_steps", []))
    calc = "\n".join(data.get("calculated", [])) or "none"
    resp = chat(
        provider=provider,
        messages=[
            {"role": "system", "content": CHECK_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nWORKED STEPS:\n{steps}\n\nCALCULATOR RESULTS:\n{calc}"},
        ],
        format=CHECK_SCHEMA,
        options=STRICT_OPTIONS,
    )
    return parse_json(resp.message.content, {"ok": True, "problem": "", "corrected_answer": ""})


def tutor_answer(question: str, history=None, provider=LOCAL) -> dict:
    chunks, best, in_syllabus = index.search(question)
    context = format_context(chunks) if in_syllabus else NO_CONTEXT

    draft, calc = "", []
    if in_syllabus and is_calculation(question):
        draft, calc = solve_with_tools(question, context, provider)

    user = f"SYLLABUS CONTEXT:\n{context}\n\nQUESTION: {question}"
    if calc:
        user += "\n\nCALCULATOR RESULTS (use exactly):\n" + "\n".join(calc)
    if draft:
        user += f"\n\nDRAFT SOLUTION:\n{draft}"

    past = [
        {"role": m["role"], "content": str(m.get("content", ""))[:1500]}
        for m in (history or [])
        if m.get("role") in ("user", "assistant")
    ][-8:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *FEW_SHOT, *past, {"role": "user", "content": user}]
    resp = chat(provider=provider, messages=messages, format=ANSWER_SCHEMA, options=OPTIONS)
    data = parse_json(resp.message.content, {"in_syllabus": in_syllabus, "hint": "", "worked_steps": [], "citation": "", "check_question": ""})
    data["calculated"] = calc
    data["retrieval_score"] = round(best, 3)
    data["sources"] = ([{ "topic": c["topic"], "subtopic": c["subtopic"], "page": c["page"] } for c in chunks] if in_syllabus else [])
    if SELF_CHECK and data.get("worked_steps"):
        data["check"] = self_check(question, data, provider)
    return data


def make_activity(topic: str, provider=LOCAL) -> dict:
    chunks, _, in_syllabus = index.search(topic, k=3)
    context = format_context(chunks) if in_syllabus else NO_CONTEXT
    resp = chat(
        provider=provider,
        messages=[
            {"role": "system", "content": ACTIVITY_PROMPT},
            {"role": "user", "content": f"SYLLABUS CONTEXT:\n{context}\n\nTOPIC: {topic}"},
        ],
        format=ACTIVITY_SCHEMA,
        options=OPTIONS,
    )
    return parse_json(
        resp.message.content,
        {"title": "Activity of integration", "scenario": "", "task": "", "materials": [], "guiding_steps": [], "success_criteria": [], "citation": ""},
    )


def warm_up():
    chat(provider=LOCAL, messages=[{"role": "user", "content": "Reply with the word ready."}], options={"num_predict": 5})
