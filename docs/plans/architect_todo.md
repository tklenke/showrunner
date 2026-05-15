# Architect TODO

Open decisions and phased work for the showrunner engine.
For the stable design record, see `architecture.md`.
For resolved decisions, see git log.

---

## Known Issues (from playthrough)

- [x] **Inline NPC stats missing from check identification** — addressed by programmer
  task 4.37. Inline NPCs get an optional flat stats block in the scene YAML (same shape
  as minion_groups). `_build_char_stats` extended to cover both. `render_inline_npc_prompt`
  replaces the bare `key_traits` string so inline NPCs enter the NPC wave with name,
  pronoun, role, and mechanical context.

- [x] **Ruling actor ID doesn't reliably match party_stats keys** — addressed by programmer
  task 4.38. `_build_actor_name_map` builds a lowercase display-name → char_id lookup at
  session start from all character sources. `_make_ruling_callback` normalises the actor
  string through this map before touching party_stats.

---

## Open Decisions

Items that have not yet been fully resolved. These need an answer before the relevant
implementation phase begins.

- [x] **SR-driven beat advancement** — Ratified. See programmer task 4.40.

- [ ] **Auto-narrated character departures** — When a beat transition drops characters via
  `remove_npcs`, the Narrator could generate a plausible in-world exit for each. Deferred:
  for the current playtest, departures are handled by beat opener `narrator_notes` written
  directly in the scene YAML (e.g. C3-P9 bolts through a side door in `gamorrean_rumble`).
  Revisit when scenes have beats with dynamic or unanticipated character drops.

- [x] **Context window pre-flight check** — Implemented. `max_context_tokens` field added
  to all agents in `agents.yaml`; `call_llm()` estimates tokens as `(len(system)+len(user))//4`
  and logs a warning via `showrunner.llm` logger if the limit would be exceeded.

- [x] **Manual dice input format** — Ratified. Single-letter keys with counts; spaces
  tolerated. Letters: S=Success, A=Advantage, T=Triumph, F=Failure, H=Threat, D=Despair.
  Example: `S2A1T1` = 2 Successes, 1 Advantage, 1 Triumph. `S2 A1 T1` also valid.
  See game_loop.md Step 6 for the full spec.

---

## Phase 0: Pre-Implementation Setup

- [ ] Parse Genesys Core Rulebook into indexed sections (`skin/rules/`)
  - `rules/index.md`, `rules/dice.md`, `rules/combat.md`, `rules/skills.md`
- [ ] Verify LiteLLM can reach llama.cpp on Alien and LM Studio on Sardinia

---

## Phase 4: MVP Scene — Bargos Mansion

Target: run the full Bargos mansion scene from *Debts to Pay* end-to-end.

Scene covers: arrival, audience with Bargos, the Gamorrean Rumble combat encounter.
Reference: `skin/Game_masters_kit.pdf` Acts 1–2.

Phases 5 and 6 are **not required** for this phase. The Show Runner operates with the
specific rules and NPC stats for this scene baked inline — no `rules_lookup()` tool needed.

- [ ] Prompts log enhancements (tasks 4.34–4.35): call ID, character label, --dump-prompts full capture
- [ ] Show Runner: manage beat progression, Gamorrean arrival ticking clock
- [ ] Narrator: beat openers and session log entries
- [ ] Actors: voice Bargos, Genko, C3-P9, Gamorreans — using `render_actor_prompt()`
- [ ] Resolution pipeline: handle Vigilance check (spotting Gamorreans), Brawl/Melee combat checks
  - Show Runner system prompt includes the specific rules needed for this scene inline
  - `rules_lookup()` is a future Phase 5 concern
- [ ] CLI: player turn prompt, `!` directive injection, manual dice input option
- [ ] Play through the scene; identify and fix issues

---

## Phase 5: Genesys Rules Parser (skin)

Needed before Phase 7. Not blocking Phase 4.

- [ ] Script to extract sections from Genesys Core Rulebook PDF → `skin/rules/`
- [ ] `rules/index.md` — section list with page references
- [ ] Priority sections: `rules/dice.md`, `rules/combat.md`, `rules/skills.md`, `rules/talents.md`
- [ ] Wire `rules_lookup()` tool in Show Runner agent — keyword search against indexed sections

---

## Phase 6: OggDude Data Ingestion (skin)

Needed before Phase 7. Not blocking Phase 4.

- [ ] `tools/xml_to_md.py` — converts OggDude XML exports to structured Markdown
- [ ] Output: `skin/data/weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Validate Show Runner can look up a weapon stat (e.g., Gamorrean vibro-ax) from converted data

---

## Phase 7: Full Gavos Adventure

- [ ] Convert all 15 mine rooms to scene YAML
- [ ] Ticking clock: storm barrier generator countdown in `scene_state.yaml`
- [ ] Lookout vehicle chase (cloud car space/planetary combat variant)
- [ ] Way station encounter and miner rescue
- [ ] Final negotiation with Bargos (Charm check resolution)

### Character Memory and Inventory (Phase 7 design)

**Background:** During the Bargos negotiation (scene_0), Kae successfully used directness
to win terms from Bargos and received a data chip with a smuggler contact. Two distinct
things need to survive scene transitions: relational/narrative memory, and a concrete item.

---

#### Narrative memory — `state/memories/{char_id}.md`

At significant moments the Show Runner appends a structured entry to a per-character
memory file. "Significant" means: a major check succeeded or failed with story
consequences, a relationship changed, or a secret was learned.

Entry format:

```
## [Scene {N}, Beat: {beat_id}]
{1–3 sentences of plain prose describing what happened and why it matters to this character.}
```

**Who writes it:** The Show Runner, as an optional extra call at beat transitions (not
every turn — only when SR beat advancement fires `ADVANCE`, i.e. a beat actually ended).
If the beat had no significant check or story event, the SR outputs `NONE` and no entry
is written.

**How it's used:** At scene load and after each beat transition, the most recent N entries
(suggested: last 5, ~500 tokens) are appended to the character's system prompt under a
`## Memory` heading. This keeps the context window bounded regardless of session length.

**Scope:** PC and Companions only. NPCs do not carry memory across scenes; their
characterisation is owned by the scene YAML.

---

#### Inventory — `state/party_inventory.yaml`

A simple list of items held by the party, keyed by character. Items are concrete objects
with story or mechanical implications (data chips, weapons, credits, keycards). Pure
narrative flavor ("grudging respect from Bargos") lives in the memory file, not here.

Schema sketch:

```yaml
kae:
  - id: bargos_contact_chip
    name: "Data chip — Bargos contact"
    description: >
      A worn chip smelling of ozone. Bargos called the contact 'a useful distraction' —
      implied rival. Unknown name.
    acquired: "scene_0 / bargos_audience"
    mechanical_effect: ""      # filled in when the contact becomes actionable
```

**Who writes it:** The orchestrator, not an LLM — item acquisition is always a direct
consequence of a story event the SR already ruled on (e.g. Bargos slides the chip across
the floor). The scene YAML can declare `loot` entries on a beat, and on beat advance the
orchestrator moves them into `party_inventory.yaml` deterministically.

**How it's used:** Inventory is shown to the player in a future `--status` command and
injected into relevant agent contexts (e.g. Show Runner when ruling on a check that
involves a held item).

---

#### Scene transition checklist (Phase 7 addition)

When a scene ends, before loading the next scene:

1. SR writes memory entries for each PC/Companion with a significant event this scene.
2. Orchestrator appends any declared `loot` from the final beat to `party_inventory.yaml`.
3. `scene_state.yaml` is reset for the new scene (existing `--reset` logic).
4. Memory files and `party_inventory.yaml` are **not** reset — they are the cross-scene
   persistent layer.

---

#### Open questions (to answer when Phase 7 begins)

- How many memory entries to include in context? Start with 5; tune during playthrough.
- Does the PC (User) get a memory file, or is their memory implicit in session_log.md?
- Should `loot` be declared in scene YAML beats, or always written manually by Tom?
- Does `mechanical_effect` on inventory items need a standard schema, or free-text for now?

---

## Phase 8: Polish and Extensibility

- [ ] Document the skin/ schema so other skins can be built (the Star Wars skin is the reference impl)
- [ ] Session resume: save/restore `state/` between sessions
- [ ] Consider richer CLI output (colour, formatted stat blocks)

---

## Phase 100: Web App (Starlette)

Not scheduled. May come after Phase 4 playthrough or much later.

**Goal:** Replace the terminal CLI with a browser-based UI. Better markdown rendering,
remote access, multiple concurrent users (feedback testers initially, more later).

**Approach:** SSE + HTTP POST + minimal HTML/JS frontend. Single async process handles
all concurrent sessions on one event loop.

- SSE (Server-Sent Events) streams narrative output to the browser.
- HTTP POST carries player input back to the server.
- Starlette directly — not FastAPI. FastAPI adds auto-docs, Pydantic validation, and
  dependency injection; none are needed here. Starlette has everything required.

**Estimated effort:** ~5–6 days of focused work (the async refactor is the real risk).

### Key decisions

- **v0: single user only.** No state isolation — existing `state/` directory as-is.
  Multi-user session isolation is a future concern.
- **Typed SSE events.** The generator yields dicts, not bare strings. The browser
  inspects `type` to decide how to render. Defined event types:
  - `{"type": "narrative", "text": "..."}` — prose, rendered via Marked.js
  - `{"type": "status", "text": "..."}` — beat/turn header
  - `{"type": "dice_prompt", "actor": "...", "skill": "...", "pool": "...", "difficulty": "...", "notes": "..."}` — show pool, await input or auto-roll
  - `{"type": "player_prompt"}` — show player action input box
  - `{"type": "parse_error", "context": "..."}` — parse failure, await correction
  - `{"type": "session_end", "reason": "..."}` — scene complete or quit
- **Verbose mode removed.** `_beat_prompt` and `--verbose` flag eliminated. Beat
  progression is fully SR-driven (4.40). Manual beat override is gone.
- **Session log gets richer writes.** SR beat decisions, check specs, rulings, and
  plan updates are logged to `state/session_log.md`. Currently only resolution
  narrative is written; the log should be a complete debug trail.
- **Input suspension: 3 points** (was 4 — beat override removed):
  - Player action prompt
  - Dice input (loop — suspends once per check spec)
  - Parse failure correction

### Stack

```
nginx      — production only: TLS, static files, reverse proxy
uvicorn    — ASGI server (uvicorn directly, not gunicorn)
starlette  — routing, SSE, session middleware, static file serving
HTML/JS    — static, served by nginx in production / starlette in dev
```

Dev/test: run `uvicorn app:app --reload` and hit localhost:8000 directly. No nginx.

### Capacity

On a t4g.small (~$12/month, 2 vCPU, 2GB RAM): the bottleneck is memory, not CPU or
network. Each active session holds scene data, character files, and state in memory —
roughly 10–20MB. Usable RAM after OS/process overhead is ~1.5GB, giving **75–150
concurrent active sessions** before memory pressure. CPU is negligible (almost entirely
async I/O wait on LLM calls).

### Work breakdown

- [ ] **Async LLM calls** (~half day) — `call_llm()` becomes `call_llm_async()` using
  `litellm.acompletion()`. All callers in `runner.py` updated to `await`.

- [ ] **Turn loop async refactor** (~2 days, the real work) — convert `run_turn_loop()`
  to an async generator that yields typed events. Replace `print()` with `yield`.
  Replace `input()` with `await queue.get()` at the 3 suspension points. The queue
  (`asyncio.Queue`) is passed in at session start. Remove `_beat_prompt` and verbose
  mode. Add richer session log writes throughout.

- [ ] **CLI adapter** (~half day) — wrap the async generator for terminal use. Input
  adapter: `await loop.run_in_executor(None, input, prompt)`. Print events to stdout.

- [ ] **Starlette layer** (~half day) — SSE endpoint streams generator events as JSON.
  POST endpoint puts player input into the session queue. Session manager holds
  `{session_id: (generator, queue)}`. Static file serving for frontend.

- [ ] **Frontend** (~1 day) — `index.html` + JS. SSE event handler dispatches on
  `type`: narrative → Marked.js render; dice_prompt → show pool + input form;
  player_prompt → show action input box. No framework needed at this scale.

- [ ] **Deployment** (~half day) — systemd service, nginx reverse proxy on AWS instance.

### Session persistence (v1)

Three levels of connection disruption:

- **Level 1 — micro-hiccup** (milliseconds, packet loss): TCP handles it transparently.
  Not our problem.
- **Level 2 — blink** (seconds, SSE drops and reconnects): treated identically to
  Level 3. No special handling.
- **Level 3 — full disconnect** (browser closed, hours later): full reset. Same as
  `--reset` from the CLI — scene 0, beat 0, all stats cleared.

One behavior for all disconnects: session dies, state is wiped, player starts fresh.
No resume logic, no partial state management, no buffering. This is acceptable because
disconnects are rare on a stable wired/wireless home connection to AWS.

### Session persistence (v2 — if the tool gains traction)

Add a **Save** button, enabled only when the engine is idle at the player action prompt
(the one clean break in the turn loop). On press, snapshot the 3 state files
(`scene_state.yaml`, `party_stats.yaml`, `session_log.md`) to `state/saves/save_TIMESTAMP/`.

On reconnect, if a save exists for this session, restore from it instead of full reset.
Sessions identified by a **cookie** (UUID issued on first connection, `response.set_cookie()`
— 5 lines, no middleware needed). Cookie survives browser close, so returning hours later
still finds the right save. Clearing cookies loses the save; opening two tabs conflicts
(user error for a single-player game).

If multi-device access is ever needed, swap cookie-keyed saves for login-keyed saves.

### Open decisions

- Short-term terminal improvement: add `rich` library for markdown rendering in CLI.
  Zero architecture change, one afternoon. Worth doing regardless of web app timing.
- Authentication: for 1–2 feedback users, no auth needed. Revisit before opening to
  many users.
