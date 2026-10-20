"""Deterministic offline model — the default, an ADK BaseLlm.

This is the ADK counterpart of muse-agent's MockProvider. It exists so
the whole system runs and can be tested with no API key. ADK calls
``generate_content_async(llm_request)``; the request carries the
conversation as genai Contents plus the tool table. The rules mirror
the original provider's, adapted to that shape:

  - "echo: X"            -> emit one function call to the echo tool,
                            then report its result on the next call
  - "time" / "现在几点"   -> call the now tool, then report its result
  - "list: PATH"         -> call list_dir, then report its result
  - "skill: NAME"        -> call load_skill, then report its result
  - "remember: X"        -> call remember (a write tool: approval gates it)
  - "subagent: TASK"     -> transfer_to_agent the worker subagent
                            (only when the agent has sub_agents)
  - anything else        -> answer directly, prefixed as a mock reply

Only tool results that arrived *after* the latest user message count
as answers to it — earlier turns must never leak into a new turn, and
transfer bookkeeping calls are not treated as tool answers.
"""
from __future__ import annotations

from typing import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

_IGNORED_CALLS = {"transfer_to_agent"}


def _format_response(name: str, response: object) -> str:
    if isinstance(response, dict):
        if set(response) == {"result"}:
            return str(response["result"])
        if "error" in response:
            return str(response["error"])
    return str(response)


class MockLlm(BaseLlm):
    """Rule-driven stand-in model. Stateless: all state is in the
    request, exactly like a real provider behind ADK."""

    async def generate_content_async(
            self, llm_request: LlmRequest,
            stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        yield self._respond(llm_request)

    # -- request reading ------------------------------------------------
    def _respond(self, request: LlmRequest) -> LlmResponse:
        contents = list(request.contents or [])
        last_user_idx = -1
        for i, content in enumerate(contents):
            if content.role == "user" and any(
                    p.text for p in (content.parts or [])):
                last_user_idx = i
        if last_user_idx == -1:
            return self._text("(mock) 没有收到用户消息。")
        after = contents[last_user_idx + 1:]
        results: list[tuple[str, object]] = []
        for content in after:
            for part in content.parts or []:
                fr = part.function_response
                if fr is not None and fr.name not in _IGNORED_CALLS:
                    results.append((fr.name, fr.response))
        if results:
            joined = "; ".join(
                f"{name} -> {_format_response(name, resp)}"
                for name, resp in results)
            return self._text(f"工具结果：{joined}")
        text = "".join(p.text or "" for p in
                       contents[last_user_idx].parts or []).strip()
        if "你的任务是：" in text:
            # Subagent brief: the snapshot above the marker is context,
            # not commands — rules match only the briefed task itself.
            task = text.split("你的任务是：", 1)[1]
            task = task.split("\n只做这件事", 1)[0].strip()
        elif text.lower().startswith("subagent:"):
            task = text[len("subagent:"):].strip()
        else:
            task = text
        available = set((request.tools_dict or {}).keys())
        low = task.lower()
        if low.startswith("echo:") and "echo" in available:
            return self._call("echo", {"text": task[5:].strip()})
        if ("现在几点" in task or "time" in low) and "now" in available:
            return self._call("now", {})
        if low.startswith("list:") and "list_dir" in available:
            return self._call(
                "list_dir", {"path": task[5:].strip() or "."})
        if low.startswith("skill:") and "load_skill" in available:
            return self._call("load_skill", {"name": task[6:].strip()})
        if low.startswith("remember:") and "remember" in available:
            return self._call("remember", {"text": task[9:].strip()})
        if (text.lower().startswith("subagent:")
                and "transfer_to_agent" in available):
            return self._call("transfer_to_agent",
                              {"agent_name": "worker"})
        return self._text(
            f"（mock 回复）我收到了：{task}。"
            "接入真实模型后，这里会是模型的回答。")

    # -- response shaping -------------------------------------------------
    @staticmethod
    def _text(text: str) -> LlmResponse:
        return LlmResponse(
            content=types.Content(
                role="model", parts=[types.Part(text=text)]),
            turn_complete=True)

    @staticmethod
    def _call(name: str, args: dict) -> LlmResponse:
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_function_call(name=name, args=args)]),
            turn_complete=True)
