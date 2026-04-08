"""Claude Code CLI subprocess wrapper.

Bypasses HTTP SDKs because the Anthropic Messages API rejects sk-ant-oat01-
OAuth tokens (anthropics/claude-code#37205) and litellm's OAuth path is
broken (BerriAI/litellm#19618). The local `claude` CLI picks up
CLAUDE_CODE_OAUTH_TOKEN from the environment and routes through the user's
Claude Max subscription.
"""
import asyncio
import json
from dataclasses import dataclass

# Block every tool — the extractor only needs JSON text output, and the worker
# container should never let the model touch the filesystem or network.
DISALLOWED_TOOLS = (
    "Read,Edit,Write,Bash,Glob,Grep,WebFetch,WebSearch,"
    "Agent,NotebookEdit,Skill,TaskCreate,TaskUpdate,TaskList"
)


@dataclass
class ClaudeCLIResult:
    content: str
    input_tokens: int
    output_tokens: int


async def call_claude_cli(
    system_prompt: str,
    user_prompt: str,
    model: str = "sonnet",
    timeout_s: float = 360.0,
    max_budget_usd: float = 1.0,
) -> ClaudeCLIResult:
    """Invoke `claude -p` as a subprocess. Inherits CLAUDE_CODE_OAUTH_TOKEN from env.

    With OAuth/Max subscription auth, calls cost $0 in real money but the CLI
    still computes a virtual cost and enforces --max-budget-usd, so set it
    generously (1.0 is plenty for a single extraction call).
    """
    args = [
        "claude", "-p", user_prompt,
        "--append-system-prompt", system_prompt,
        "--output-format", "json",
        "--model", model,
        "--no-session-persistence",
        "--disallowedTools", DISALLOWED_TOOLS,
        "--max-budget-usd", str(max_budget_usd),
    ]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"claude CLI timed out after {timeout_s}s")

    if proc.returncode != 0:
        err = (stderr or b"").decode(errors="replace")[:300]
        raise RuntimeError(f"claude CLI exit {proc.returncode}: {err}")

    try:
        data = json.loads(stdout.decode())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"bad JSON from claude CLI: {e}: {stdout[:200]!r}")

    if data.get("is_error"):
        raise RuntimeError(f"claude CLI returned error: {data.get('result', 'unknown')}")

    usage = data.get("usage") or {}
    return ClaudeCLIResult(
        content=(data.get("result") or "").strip(),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )
