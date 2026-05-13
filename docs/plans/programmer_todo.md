# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/terminology.md` — **canonical terms; read before touching any character or turn-loop code**
- `docs/plans/game_loop.md` — **source of truth for the turn loop; if code diverges, the code is wrong**
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — End-to-End Scene Playthrough

---

### [ ] 4.34 — Prompts log: call ID and character label

Improves the per-call log line with a sequential ID and an optional character label so
loops like the NPC wave show which character each call belongs to.

**`call_llm()` — add `label: str = ""`**

```python
def call_llm(agent_name, system_prompt, user_message, label: str = "") -> str:
```

When `label` is provided, the step column in the log becomes `step[label]`.
Example: `run_npc_wave[bargos_the_hutt]` instead of `run_npc_wave`.

**Callers that must pass `label`** (all loop over characters — pass the id):

| Runner function | Inner loop variable | Pass as |
|---|---|---|
| `run_npc_wave` | `npc_id` | `label=npc_id` for both actor + narrator calls |
| `run_companion_wave` | `pc_id` | `label=pc_id` |
| `run_checks` | `char_id` | `label=char_id` |
| `run_last_actions` | `actor_id` | `label=actor_id` |
| `run_plan_update` (individual loop) | `char_id` | `label=char_id` |

All other `call_llm()` call sites leave `label` at its default (no change needed).

**`_PromptLogger` — add sequential call ID**

Add an integer counter `_call_id: int = 0` to `_PromptLogger.__init__`. Increment
before each log write. Format as 4-digit zero-padded in the first column.

**New log format:**

```
0001  HH:MM:SS  narrator     sardinia  run_beat_opener                1842p →  312r
0002  HH:MM:SS  actors       sardinia  run_npc_wave[bargos_the_hutt]  2103p →  445r
0003  HH:MM:SS  narrator     sardinia  run_npc_wave[bargos_the_hutt]   198p →   61r
0004  HH:MM:SS  actors       sardinia  run_npc_wave[kaelen_sunara]    2098p →  389r
```

**`_PromptLogger.log()` signature change:**

```python
def log(self, agent, server, step, prompt_len, response_len, label="") -> None:
```

**`call_llm()` passes `label` to `_prompt_logger.log()`.**

**Tests:**
- Log line starts with a 4-digit zero-padded ID
- Second call has ID one higher than first
- `call_llm(..., label="bargos")` → step column contains `run_npc_wave[bargos]`
- `call_llm(...)` with no label → step column is just the function name, no brackets

---

### [ ] 4.35 — Prompts log: --dump-prompts flag writes full prompt/response MD files

When `--dump-prompts` is passed on the CLI, every `call_llm()` writes a single Markdown
file containing the full system prompt, user message, and response. Files are named by
call ID so they sort alongside the prompts log.

**CLI flag — `main.py`:**

```python
parser.add_argument("--dump-prompts", action="store_true",
                    help="Write full prompt+response to logs/prompts/ for each call")
```

Pass `args.dump_prompts` into `run_turn_loop()` and on to `setup_instrumentation()`.

**`setup_instrumentation()` — add `dump_prompts: bool = False`:**

When `True`, create `logs/prompts/` subdirectory and pass it as `dump_dir` to
`setup_llm_logging()`.

**`setup_llm_logging()` — add `dump_dir: Path | None = None`:**

Passes `dump_dir` into `_PromptLogger.__init__`.

**`_PromptLogger` — write MD file when `dump_dir` is set:**

After incrementing `_call_id`, if `self._dump_dir` is not None, write:

```
logs/prompts/{id:04d}_{agent}_{step}.md
```

where `step` is already `step[label]` if label is present.

File contents:
```markdown
# System
{system_prompt}

# User
{user_message}

# Response
{response}
```

`_PromptLogger.log()` therefore needs `system_prompt` and `user_message` and `response`
added as parameters. `call_llm()` passes them. When `dump_dir` is None the extra args
are ignored (no file I/O).

**Updated `_PromptLogger.log()` signature:**

```python
def log(self, agent, server, step, prompt_len, response_len,
        label="", system_prompt="", user_message="", response="") -> None:
```

**`run_turn_loop()` signature change:**

```python
def run_turn_loop(scene, verbose=False, dump_prompts=False) -> None:
```

**Tests:**
- `--dump-prompts` not set → `logs/prompts/` not created, no MD files written
- `--dump-prompts` set → file `logs/prompts/0001_narrator_run_beat_opener.md` created
- MD file contains `# System`, `# User`, `# Response` sections with correct content
- File name uses `step[label]` form when label is present

---

### [~] 4.33 — End-to-End Scene Playthrough

No tests for this task — this is exploratory play. Run `src/showrunner/main.py` and
play through `skin/scenes/scene_0.yaml` (Bargos mansion) from entry to exit condition.

Checklist before calling Phase 4 done:
- [ ] Scene entry read-aloud is delivered by the Narrator
- [ ] Bargos audience beat runs; Negotiation check can be triggered
- [ ] Gamorrean warning beat triggers; Vigilance check fires
- [ ] Gamorrean Rumble combat resolves with dice (auto or manual input)
- [ ] Wounds are tracked correctly; minions die at wound threshold multiples
- [ ] Mission brief beat runs after combat
- [ ] Scene exits cleanly; scene_state.yaml updated

Issues found during play are bugs — fix them. If something requires an architectural
decision, stop and raise it with Tom.

---

## Phase 5 — Genesys Rules Parser

Do not begin Phase 5 until Phase 4 has been played through successfully.

This phase delivers the data that `rules_lookup()` queries. It unblocks Phase 7.

- [ ] Write a PDF extraction script: `tools/parse_rulebook.py`
  - Input: `docs/references/Genesys_Core_Rulebook.pdf`
  - Output: section files in `skin/rules/` (dice.md, combat.md, skills.md, talents.md)
  - Use `pymupdf` (already installed)
- [ ] Write `skin/rules/index.md` — section list with page references
- [ ] Implement `rules_lookup(keyword: str) -> str` in `src/showrunner/tools/rules_lookup.py`
  - Keyword search against indexed sections; returns most relevant section text
- [ ] Wire `rules_lookup()` into the Show Runner agent
- [ ] Smoke test: Show Runner can retrieve the correct rule for "critical injury", "soak", "Brawl"

---

## Phase 6 — OggDude Data Ingestion

Do not begin Phase 6 until Phase 5 is complete.

This phase replaces inline NPC stats with a proper data source for Phase 7.

- [ ] Write `tools/xml_to_md.py` — convert OggDude XML exports to structured Markdown
- [ ] Output to `skin/data/`: `weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Smoke test: Show Runner can look up Gamorrean vibro-ax damage, crit, range, special from `weapons.md`
