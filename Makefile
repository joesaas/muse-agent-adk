.PHONY: test demo

test:
	.venv/bin/python -m pytest tests/ -q

demo:
	PYTHONPATH=src .venv/bin/python -m muse_agent_adk --home /tmp/muse-agent-adk-demo demo
