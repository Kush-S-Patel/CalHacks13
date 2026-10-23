# SwarmCFO — 3-minute demo script

## Pre-flight (T−30 min)

1. Run `npm run sim` once — confirm last_sim.json writes  
2. Record local fallback video (`poc` path) before final hour  
3. Big screen: `/` · Phone: `/phone` · QR visible  
4. Seed SpacetimeDB: `npm run spacetime:publish` then open world  
5. Agent service: `npm run agents` with `ANTHROPIC_API_KEY`  

## Script

| Time | Beat |
| --- | --- |
| 0:00–0:20 | Pain: Maya alone, runway counter ticking at **11 days** |
| 0:20–0:50 | Judge presses chaos (or QR from their phone): price spike, duplicate $4.2k, late $9.2k |
| 0:50–1:40 | Show **tool calls, not chat** — BLOCKED + reason, counter SENT, Procurement vs Risk → CFO arbitrate |
| 1:40–2:20 | $1,400 **WAITING** → owner tap **Approve** → every screen updates |
| 2:20–3:00 | Close: “2,000 students here will start something alone. None can hire a finance team. This is the team.” |

## Talk track (owner UI)

> “Judges asked if this is too complex for someone without a finance background. The owner sees one number — runway — and one button — Approve. The swarm lives under the hood.”

## Fallback

If Wi-Fi / Anthropic / SpacetimeDB dies: play recorded video, or run `python poc/swarmcfo_sim.py` on projector terminal.