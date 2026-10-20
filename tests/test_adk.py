"""Offline test suite for muse-agent-adk.

Everything runs on MockLlm through the real ADK stack (LlmAgent +
Runner + InMemorySessionService): no network, no API keys.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from google.adk.events.event import Event
from google.genai import types

from muse_agent_adk.approval import (ApprovalPolicy, auto_approver,
                                       deny_approver)
from muse_agent_adk.config import Config
from muse_agent_adk.context import (AdkContextBridge, load_snapshot)
from muse_agent_adk.core.types import ToolCall
from muse_agent_adk.goals import GoalTracker
from muse_agent_adk.memory import MemoryStore
from muse_agent_adk.runtime import Agent, build_root_agent, build_session
from muse_agent_adk.scheduling import CronSpec, Job, Scheduler
from muse_agent_adk.core.events import EventBus
from muse_agent_adk.security import redact
from muse_agent_adk.skills import parse_frontmatter
from muse_agent_adk.subagents import SubagentManager


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


@pytest.fixture()
def agent_factory(home):
    agents = []

    def make(approver="unset", **cfg_kwargs):
        cfg = Config(home=home, **cfg_kwargs)
        session = (build_session(cfg) if approver == "unset"
                   else build_session(cfg, approver=approver))
        agent = Agent(session)
        agents.append(agent)
        return agent, session

    yield make
    for a in agents:
        a.close()


# ---------------------------------------------------------------- assembly

def test_root_agent_assembly(agent_factory):
    _, session = agent_factory()
    root = build_root_agent(session)
    assert root.name == "muse_agent"
    assert [a.name for a in root.sub_agents] == ["worker"]
    tool_names = {t.name for t in root.tools}
    assert {"echo", "now", "list_dir", "read_file", "load_skill",
            "memory_search", "remember",
            "connector_echo"} <= tool_names
    assert "You are Muse Agent" in root.instruction
    assert session.adk_session_id
    state = session.session_service.get_session_sync(
        app_name=session.app_name, user_id=session.user_id,
        session_id=session.adk_session_id).state
    assert "memory_index" in state  # memory -> state bridge seeded


def test_prompt_sections_and_skills_index(home):
    skill_dir = home / "skills" / "demo-helper"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-helper\ndescription: Demo skill.\n"
        "triggers: demo\n---\n\nBODY-MARKER: do the demo steps.\n",
        encoding="utf-8")
    session = build_session(Config(home=home))
    assert "demo-helper" in session.system_prompt
    meta, body = parse_frontmatter(
        (skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    assert meta["name"] == "demo-helper" and "BODY-MARKER" in body


# ------------------------------------------------------------- runner loop

def test_plain_reply(agent_factory):
    agent, _ = agent_factory()
    out = agent.run_turn("你好")
    assert "我收到了：你好" in out


def test_tool_roundtrip_echo(agent_factory):
    agent, session = agent_factory()
    out = agent.run_turn("echo: hello tools")
    assert out == "工具结果：echo -> hello tools"
    kinds = [e.type for e in session.bus.history]
    assert "turn.started" in kinds and "turn.finished" in kinds
    assert "tool.called" in kinds and "tool.finished" in kinds


def test_tool_roundtrip_now(agent_factory):
    agent, _ = agent_factory()
    out = agent.run_turn("现在几点？")
    assert out.startswith("工具结果：now -> ")


def test_no_cross_turn_tool_leak(agent_factory):
    agent, _ = agent_factory()
    first = agent.run_turn("echo: first")
    second = agent.run_turn("第二轮问题")
    assert "echo -> first" in first
    assert "我收到了：第二轮问题" in second


def test_load_skill_tool_roundtrip(home, agent_factory):
    skill_dir = home / "skills" / "demo-helper"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-helper\ndescription: Demo skill.\n---\n\n"
        "BODY-MARKER steps.\n", encoding="utf-8")
    agent, _ = agent_factory()
    out = agent.run_turn("skill: demo-helper")
    assert "load_skill -> " in out and "BODY-MARKER" in out


def test_connector_tool_via_registry(agent_factory):
    _, session = agent_factory()
    result = session.tools.execute(ToolCall(
        name="connector_echo",
        arguments={"action": "echo", "text": "via connector"}))
    assert result.ok and result.output == "via connector"


# ---------------------------------------------------------------- approval

def test_policy_read_auto_write_needs_approver():
    policy = ApprovalPolicy(approver=deny_approver)
    call = ToolCall(name="x")
    assert policy.check(call, "read").value == "allow"
    assert policy.check(call, "write").value == "deny"
    assert policy.check(call, "exec").value == "deny"


def test_policy_no_approver_is_fail_closed():
    """The deliberate fix vs muse-agent: approver=None must DENY
    write/exec instead of silently auto-approving."""
    policy = ApprovalPolicy()
    call = ToolCall(name="x")
    assert policy.check(call, "read").value == "allow"
    assert policy.check(call, "write").value == "deny"
    assert policy.check(call, "exec").value == "deny"
    policy2 = ApprovalPolicy(auto_approve_write=True)
    assert policy2.check(call, "write").value == "allow"
    assert policy2.check(call, "exec").value == "deny"


def test_remember_denied_without_approver(home, agent_factory):
    agent, _ = agent_factory()  # build_session without approver
    out = agent.run_turn("remember: 不该落盘的一条")
    assert "approval denied for tool remember" in out
    assert not list((home / "memory").glob("*.md"))


def test_remember_allowed_with_approver(home, agent_factory):
    agent, _ = agent_factory(approver=auto_approver)
    out = agent.run_turn("remember: 用户喜欢深色主题")
    assert "remember -> remembered" in out
    files = list((home / "memory").glob("*.md"))
    assert len(files) == 1
    assert "用户喜欢深色主题" in files[0].read_text(encoding="utf-8")


# --------------------------------------------------------------- subagents

def test_subagent_manager_spawn(agent_factory):
    agent, session = agent_factory()
    agent.run_turn("现在几点？")  # give the parent some history
    manager = SubagentManager(parent=session)
    result = manager.spawn("echo: 我是子代理，我完成了任务")
    assert result.ok
    assert result.output == "工具结果：echo -> 我是子代理，我完成了任务"
    assert result.session_id != session.adk_session_id  # isolated session
    kinds = [e.type for e in session.bus.history]
    assert "subagent.spawned" in kinds and "subagent.finished" in kinds


def test_subagent_depth_cap(agent_factory):
    _, session = agent_factory()
    manager = SubagentManager(parent=session, depth=2, max_depth=2)
    result = manager.spawn("echo: 不应执行")
    assert not result.ok and "深度" in result.output


def test_transfer_delegation(agent_factory):
    agent, _ = agent_factory()
    out = agent.run_turn("subagent: echo: 经 transfer 委派")
    assert out == "工具结果：echo -> 经 transfer 委派"


# ------------------------------------------------------------------ memory

def test_memory_store_roundtrip(home):
    store = MemoryStore(home)
    store.append_daily("用户在学 ADK")
    store.append_curated("用户的时区是 Asia/Shanghai")
    hits = store.search("ADK")
    assert hits and hits[0].source.startswith("memory/")
    assert "Asia/Shanghai" in store.index_text()
    path = store.append_daily("第二条")
    assert "第二条" in path.read_text(encoding="utf-8")


def test_memory_search_tool(agent_factory):
    agent, session = agent_factory()
    session.memory.append_curated("用户养了一只叫 Mochi 的猫")
    result = session.tools.execute(ToolCall(
        name="memory_search", arguments={"query": "Mochi"}))
    assert result.ok and "Mochi" in result.output


def test_snapshot_saved_in_original_format(home, agent_factory):
    agent, session = agent_factory()
    agent.run_turn("echo: 快照测试")
    snap = home / "sessions" / f"{session.id}.json"
    assert snap.exists()
    data = json.loads(snap.read_text(encoding="utf-8"))
    assert data["session_id"] == session.id
    ctx = load_snapshot(home, session.id)
    assert ctx is not None
    assert any("快照测试" in m.content for m in ctx.messages)


# ----------------------------------------------------------------- context

def test_bridge_compression_rotates_session(home):
    async def scenario():
        cfg = Config(home=home, context_budget_tokens=60,
                     keep_recent_messages=2)
        session = build_session(cfg)
        service = session.session_service
        adk = await service.get_session(
            app_name=session.app_name, user_id=session.user_id,
            session_id=session.adk_session_id)
        bridge = AdkContextBridge(budget_tokens=60, keep_recent=2)
        for i in range(8):
            await service.append_event(adk, Event(
                author="user", content=types.Content(
                    role="user", parts=[types.Part(
                        text=f"第 {i} 条很长的用户消息用来撑满预算 " * 4)])))
            await service.append_event(adk, Event(
                author="muse_agent", content=types.Content(
                    role="model", parts=[types.Part(
                        text=f"第 {i} 条回复 " * 4)])))
        new_id = await bridge.maintain(
            service, app_name=session.app_name, user_id=session.user_id,
            session_id=session.adk_session_id, agent_name="muse_agent",
            system_prompt=session.system_prompt)
        assert new_id is not None and new_id != session.adk_session_id
        rotated = await service.get_session(
            app_name=session.app_name, user_id=session.user_id,
            session_id=new_id)
        assert "context_summary" in rotated.state
        assert len(rotated.events) < len(adk.events)
        texts = "".join(
            (p.text or "") for e in rotated.events if e.content
            for p in e.content.parts)
        assert "上下文已压缩" in texts
    asyncio.run(scenario())


def test_agent_compresses_between_runs(home, agent_factory):
    agent, session = agent_factory(
        context_budget_tokens=120, keep_recent_messages=2)
    first_id = session.adk_session_id
    for i in range(5):
        agent.run_turn(f"第 {i} 轮普通对话，内容稍微长一点点用来占预算")
    assert session.adk_session_id != first_id
    kinds = [e.type for e in session.bus.history]
    assert "context.compressed" in kinds
    # the agent still answers correctly after rotation
    out = agent.run_turn("echo: 压缩后照常工作")
    assert out == "工具结果：echo -> 压缩后照常工作"


# ------------------------------------------------------- kept-from-original

def test_cron_spec_and_scheduler():
    bus = EventBus()
    scheduler = Scheduler(bus)
    job = Job(id="j1", spec=CronSpec("*/15 * * * *"), prompt="check")
    scheduler.add(job)
    from datetime import datetime
    due = scheduler.tick(datetime(2026, 10, 20, 9, 15))
    assert due == [job]
    assert scheduler.tick(datetime(2026, 10, 20, 9, 15)) == []  # dedupe
    assert bus.history[-1].type == "cron.due"


def test_redact():
    out = redact("api_key=sk-1234567890abcdef and Bearer xyz")
    assert "sk-1234567890abcdef" not in out and "xyz" not in out


def test_goals_tracker(home):
    tracker = GoalTracker(home / "goals.json")
    goal = tracker.add_goal("学会 ADK", "系统掌握")
    item = tracker.add_item("写完测试")
    assert tracker.open_items() == [item]
    assert tracker.complete_item(item.id)
    assert tracker.open_items() == []
    reloaded = GoalTracker(home / "goals.json")
    assert reloaded.goals[0].id == goal.id
