#!/usr/bin/env python3
"""Probe the free AI-video endpoints and write STATUS.md.

Why: the free tiers move constantly - a Space sleeps, a provider starts returning
Cloudflare 1010, a free tier disappears from a pricing page. Every "best free API"
list on the internet is stale the week it is written. This checks the endpoints
that actually matter and commits the result daily, so the answer is dated.

Only stdlib. Runs on a GitHub runner, not on the maintainer's machine, so a
datacenter-IP block shows up as a real signal rather than a personal quirk.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TIMEOUT = 25
UA = "free-video-status/1.0 (+https://github.com/hackermanprivate/free-video-status)"

SPACES = [
    "Wan-AI/Wan2.2-T2V-A14B",
    "Upsampler/wan-2-2-14b-text-to-video",
    "Upsampler/wan-2-2-14b-image-to-video",
    "THUDM/CogVideoX-5b",
    "multimodalart/wan2-1-fast",
]

ENDPOINTS = [
    # (label, url, method, body, what counts as "reachable without a key")
    ("Pollinations image", "https://image.pollinations.ai/prompt/status-check?width=64&height=64&nologo=true", "GET", None, "ok"),
    ("Pollinations text", "https://text.pollinations.ai/models", "GET", None, "ok"),
    ("Hugging Face API", "https://huggingface.co/api/models?limit=1", "GET", None, "ok"),
    ("Gemini API", "https://generativelanguage.googleapis.com/v1beta/models", "GET", None, "auth"),
    ("Replicate API", "https://api.replicate.com/v1/models", "GET", None, "auth"),
    ("fal API", "https://fal.run/fal-ai/flux/schnell", "POST", b"{}", "auth"),
    ("OpenAI API", "https://api.openai.com/v1/models", "GET", None, "auth"),
]


def probe(url: str, method: str = "GET", body: bytes | None = None) -> tuple[int | None, str, float]:
    req = urllib.request.Request(url, method=method, data=body, headers={"User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            head = r.read(200)
            ct = r.headers.get("Content-Type", "")
            return r.status, ct or str(head[:40]), time.time() - t0
    except urllib.error.HTTPError as e:
        text = e.read(200).decode("utf-8", "ignore")
        if "1010" in text or e.code == 1010:
            return e.code, "cloudflare block (1010)", time.time() - t0
        return e.code, text[:60], time.time() - t0
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}", time.time() - t0


def classify(code: int | None, detail: str, expectation: str) -> tuple[str, str]:
    if code is None:
        return "down", detail
    if "1010" in detail:
        return "blocked", "Cloudflare 1010 (bot check)"
    if expectation == "ok":
        return ("up", "free, no key") if code == 200 else ("down", f"http {code}")
    if expectation == "auth":
        if code in (401, 403, 400):
            return "up", f"reachable, key needed (http {code})"
        return ("up", f"http {code}") if code < 500 else ("down", f"http {code}")
    return "unknown", f"http {code}"


def space_status(space: str) -> tuple[str, str]:
    code, detail, _ = probe(f"https://huggingface.co/api/spaces/{space}")
    if code == 200:
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://huggingface.co/api/spaces/{space}", headers={"User-Agent": UA}), timeout=TIMEOUT) as r:
                data = json.loads(r.read().decode())
            stage = (data.get("runtime") or {}).get("stage")
            hw = ((data.get("runtime") or {}).get("hardware") or {}).get("current")
            if stage == "RUNNING":
                return "up", f"RUNNING on {hw}"
            return "down", str(stage)
        except Exception:  # noqa: BLE001
            return "unknown", "metadata unreadable"
    if code == 401:
        return "down", "space not found / renamed"
    return "down", f"http {code}"


def main() -> int:
    rows: list[tuple[str, str, str, str]] = []
    for space in SPACES:
        state, detail = space_status(space)
        rows.append((f"[{space}](https://huggingface.co/spaces/{space})", "ZeroGPU space", state, detail))

    for label, url, method, body, expectation in ENDPOINTS:
        code, detail, secs = probe(url, method, body)
        state, note = classify(code, detail, expectation)
        rows.append((label, "HTTP endpoint", state, f"{note} · {secs:.1f}s"))

    icons = {"up": "🟢 up", "auth": "🟡 key", "down": "🔴 down", "blocked": "⛔ blocked", "unknown": "⚪ ?"}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    up = sum(1 for r in rows if r[2] == "up")

    md = [
        "# Free AI video: what is actually working today",
        "",
        f"Last checked **{now}**. {up}/{len(rows)} endpoints answering. Auto-committed by a daily GitHub Action -",
        "if this file is old, the Action died, which is itself the answer.",
        "",
        "| Service | Kind | Status | Detail |",
        "|---|---|---|---|",
    ]
    for label, kind, state, detail in rows:
        md.append(f"| {label} | {kind} | {icons.get(state, state)} | {detail} |")

    md += [
        "",
        "## How to read this",
        "",
        "- 🟢 **up** - answering without a key, free tier usable",
        "- 🟡 **key** - endpoint is alive, needs a (free) API key",
        "- 🔴 **down** - sleeping, renamed, or erroring. Spaces sleep when idle; retry later",
        "- ⛔ **blocked** - Cloudflare 1010 or similar. The endpoint exists but refuses this network",
        "",
        "## Notes that save an afternoon",
        "",
        "- A Hugging Face Space that is `RUNNING` still has a **5 GPU-minute daily quota** per free account (2 anonymous, 40 on PRO).",
        "- The endpoint being up says nothing about the licence. Wan 2.2 is Apache-2.0 (commercial use fine); most others are not.",
        "- Paid APIs are probed too: a 401 means the service is alive and would work with a key, which is what you want to know before signing up.",
        "",
        "Generated by [`check.py`](check.py). Add an endpoint by editing the lists at the top.",
        "",
    ]

    Path("STATUS.md").write_text("\n".join(md), encoding="utf-8")
    Path("status.json").write_text(json.dumps(
        {"checked": now, "rows": [{"service": r[0], "kind": r[1], "state": r[2], "detail": r[3]} for r in rows]},
        indent=1), encoding="utf-8")
    print(f"checked {len(rows)} endpoints, {up} up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
