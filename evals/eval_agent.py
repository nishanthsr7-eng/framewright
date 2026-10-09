"""End-to-end LLM eval: can a model turn an edit request into a valid plan and a Resolve Lua script?

Each prompt runs against two hosted, OpenAI-compatible API endpoints, in two stages that mirror the real workflow:
  1. request + clip/beat facts + docs/edit-plan.md  -> edit plan JSON
  2. prompts/resolve-script.md + that plan           -> Lua script
Each run is scored on four checks:
  plan_valid   validate_plan returns no errors
  lua_parses   the Lua script parses (luaparser) and obeys the sandbox (no io, no require)
  build_ok     the bridge builds the plan on a fake Resolve and places every clip
  on_beat      every clip starts within one frame of a beat

Config (environment or .env at the repo root), for X in A and B:
  LLM_X_BASE_URL  the provider's OpenAI-compatible base URL, e.g. https://api.example.com/v1
  LLM_X_API_KEY   API key for that provider
  LLM_X_MODEL     model name sent to the endpoint
Run make_fixtures.py first.

Usage: uv run --group agent python evals/eval_agent.py [--runs 1] [--only A] [--out output/eval_agent.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

from beat_sync_mcp.plan import validate_plan

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "evals" / "fixtures"
sys.path.insert(0, str(ROOT / "resolve" / "bridge"))
import framewright_bridge as fw  # noqa: E402
import test_framewright_bridge as fakes  # noqa: E402

FPS = 25
CLIPS = {"red.mp4": "red", "blue.mp4": "blue", "green.mp4": "green"}  # 30 s each

PROMPTS = [
    ("click_120.wav", "Cut red.mp4 and blue.mp4 to the music, alternating, one shot every two beats, max 10 seconds."),
    (
        "click_90.wav",
        "Make an 8 second edit from all three clips, a new shot on every beat, in order red, blue, green.",
    ),
    ("click_140.wav", "Start on green.mp4, then switch between red and blue every four beats until 12 seconds."),
    ("click_120.wav", "Edit red, blue and green to the beat, 6 seconds total, and add a red marker named drop at 4 s."),
    (
        "click_90.wav",
        "Two-track edit for 8 seconds: blue on track 1 cut every two beats, red on track 2 for beats 3-4.",
    ),
]

PLAN_SYSTEM = """You write edit plans for Framewright. Reply with one ```json code block only: the plan.
Use version "0.1", fps {fps}, 1280x720. Copy the beats below into beat_grid.beats.
Use file paths exactly as given. Clip `in`/`out` are seconds in the source; `at` is seconds on the timeline.

Plan format:
{doc}"""


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        k, sep, v = line.strip().partition("=")
        if sep and not k.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def endpoint(name: str) -> dict | None:
    cfg = {k: os.environ.get(f"LLM_{name}_{k.upper()}", "") for k in ("base_url", "api_key", "model")}
    return cfg if all(cfg.values()) else None


def chat(cfg: dict, system: str, user: str) -> str:
    body = {
        "model": cfg["model"],
        "temperature": 0,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {cfg['api_key']}"}
    req = urllib.request.Request(cfg["base_url"].rstrip("/") + "/chat/completions", json.dumps(body).encode(), headers)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def code_block(text: str, lang: str) -> str | None:
    m = re.search(rf"```{lang}\s*\n(.*?)```", text, re.S) or re.search(r"```\w*\s*\n(.*?)```", text, re.S)
    return m.group(1) if m else None


def make_clips(tmp: Path) -> None:
    for name, color in CLIPS.items():
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:size=320x180:rate={FPS}"]
            + ["-t", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp / name)],
            check=True,
            timeout=120,
        )


def lua_check(src: str) -> str | None:
    """None if the script parses and follows the sandbox rules, else the failure type."""
    from luaparser import ast  # noqa: PLC0415

    try:
        ast.parse(src)
    except Exception:
        return "lua syntax error"
    if re.search(r"\bio\.|\brequire\s*[\(\"']", src):
        return "lua uses io/require"
    return None


def run_one(cfg: dict, music: str, request: str, beats: list[float], tmp: Path, doc: str, script_prompt: str):
    fails: list[str] = []
    facts = {
        "clips": {n: {"duration": 30.0, "fps": FPS} for n in CLIPS},
        "music": music,
        "beats": [b for b in beats if b <= 20],
    }
    user = f"{request}\n\nFacts:\n{json.dumps(facts)}"
    try:
        reply = chat(cfg, PLAN_SYSTEM.format(fps=FPS, doc=doc), user)
    except Exception as e:
        return {"fails": [f"api error: {type(e).__name__}"]}
    raw = code_block(reply, "json")
    try:
        plan = json.loads(raw or "")
    except json.JSONDecodeError:
        return {"fails": ["plan not JSON"]}

    plan_path = tmp / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    try:
        v = validate_plan(str(plan_path), base_dir=str(tmp))
    except Exception as e:
        v = {"valid": False, "errors": [f"validator crashed: {type(e).__name__}"], "warnings": []}
    plan_valid = v["valid"]
    if not plan_valid:
        fails += sorted({"plan: " + re.sub(r"clips\[\d+\]: |[\d.]+s?", "", e).strip() for e in v["errors"]})
    on_beat = plan_valid and not any("off the nearest beat" in w for w in v["warnings"])
    if plan_valid and not on_beat:
        fails.append("cuts off beat")

    build_ok = False
    try:
        r = fakes.Resolve()
        report = fw.build_from_plan(r, plan, base_dir=str(tmp), log=lambda *_: None)
        build_ok = report["clips_placed"] == len(plan.get("clips") or []) > 0 and not report["skipped"]
    except Exception as e:
        fails.append(f"build crashed: {type(e).__name__}")
    else:
        if not build_ok:
            fails.append("build missed clips")

    lua_ok = False
    try:
        lua_reply = chat(
            cfg, "Follow the instructions exactly.", script_prompt.replace("PASTE YOUR EDIT PLAN HERE", raw or "")
        )
        lua = code_block(lua_reply, "lua")
        err = "no lua block" if lua is None else lua_check(lua)
        lua_ok = err is None
        if err:
            fails.append(err)
    except Exception as e:
        fails.append(f"api error: {type(e).__name__}")

    return {"plan_valid": plan_valid, "lua_parses": lua_ok, "build_ok": build_ok, "on_beat": on_beat, "fails": fails}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1, help="repeats per prompt")
    ap.add_argument("--only", choices=["A", "B"], help="test one endpoint")
    ap.add_argument("--out", default=str(ROOT / "output" / "eval_agent.json"))
    args = ap.parse_args()

    load_env()
    names = [args.only] if args.only else ["A", "B"]
    found = {n: endpoint(n) for n in names}
    missing = [n for n, c in found.items() if c is None]
    if missing:
        sys.exit(f"Set LLM_{missing[0]}_BASE_URL, _API_KEY and _MODEL (env or .env); see this file's docstring.")
    cfgs = {n: c for n, c in found.items() if c is not None}

    truth = json.loads((FIX / "ground_truth.json").read_text(encoding="utf-8"))["audio"]
    doc = (ROOT / "docs" / "edit-plan.md").read_text(encoding="utf-8")
    script_prompt = (ROOT / "prompts" / "resolve-script.md").read_text(encoding="utf-8").split("\n---\n", 1)[1]

    results = {}
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        make_clips(tmp)
        for name, cfg in cfgs.items():
            runs = []
            for music, request in PROMPTS:
                (tmp / music).write_bytes((FIX / music).read_bytes())
                for _ in range(args.runs):
                    res = run_one(cfg, music, request, truth[music]["beats"], tmp, doc, script_prompt)
                    runs.append({"prompt": request, **res})
                    print(f"[{name}] {'ok' if not res['fails'] else '; '.join(res['fails'])}", file=sys.stderr)
            results[name] = {"model": cfg["model"], "runs": runs}

    checks = ["plan_valid", "lua_parses", "build_ok", "on_beat"]
    print("| model | runs | " + " | ".join(checks) + " | all pass | common failures |")
    print("|---|---|" + "---|" * (len(checks) + 2))
    for res in results.values():
        runs = res["runs"]
        n = len(runs)
        allp = sum(not r["fails"] for r in runs)
        common = Counter(f for r in runs for f in r["fails"]).most_common(3)
        print(
            f"| {res['model']} | {n} | "
            + " | ".join(f"{sum(bool(r.get(k)) for r in runs)}/{n}" for k in checks)
            + f" | {allp}/{n} | "
            + (", ".join(f"{f} ({c})" for f, c in common) or "-")
            + " |"
        )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nraw results: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
