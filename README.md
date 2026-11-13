# free-video-status

**Which free AI-video endpoints are actually answering right now?** Checked daily by a GitHub Action, committed to this repo, dated.

Almost every "best free AI video API" list is written once and never verified again. Spaces sleep, tiers vanish, providers start refusing datacenter IPs. This repo keeps a live answer instead.

See the current table: **[STATUS.md](STATUS.md)**

## What it checks

- **Hugging Face Spaces** that can generate video on ZeroGPU (Wan 2.2 text-to-video and image-to-video, CogVideoX, Wan 2.1 fast) - read as `RUNNING` / sleeping / renamed
- **Free-with-no-key endpoints** - Pollinations image and text
- **Paid APIs probed for reachability** - Gemini, Replicate, fal, OpenAI. A 401 means the service is alive and a key would work, which is what you want to know before signing up
- **Cloudflare 1010 style blocks** are reported separately from "down", because a bot check is not an outage

## Run it yourself

```bash
python3 check.py      # rewrites STATUS.md and status.json
```

No dependencies, no keys. Python 3.10+.

Add an endpoint: edit the `SPACES` or `ENDPOINTS` list at the top of `check.py`. Each entry is a label, a URL, and whether "no key needed" or "key needed" is the healthy state.

## Why the daily commit instead of a badge

A badge only renders one bit. The useful part is the detail column - "Space sleeping", "key needed", "Cloudflare 1010" - and the fact that a stale file means the Action itself broke. Both are visible in a table and invisible in a badge.

## Caveats

- Runs from GitHub's runners, so results describe the network those runners see. Your IP may be blocked where theirs is not (or the reverse).
- An "up" endpoint can still be unusable in practice - quota exhausted, model removed from the Space, queue 40 minutes long. Status is necessary, not sufficient.
- These are third-party free tiers. Licences and limits are theirs to change, usually without notice.

MIT.
