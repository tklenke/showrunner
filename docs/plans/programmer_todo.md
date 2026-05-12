# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 1 — DiceRoller

The dice roller is the critical path. Every other system (Referee, combat, skill checks)
depends on it. Do nothing else until this is complete and fully tested.

### Setup

Before writing any code:
```bash
source venv/bin/activate    # or: python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

All tests: `pytest tests/`

---

### [x] 1.1 — Face Table Coverage Tests

File: `tests/test_dice_roller.py`

Write tests that verify every die type has the correct number of faces and that the face
distribution matches the Genesys Core Rulebook (Table I.1-2, p.11). The face tables are
already in `src/showrunner/tools/dice_roller.py` — these tests lock them in.

Tests to write:
- `test_boost_has_6_faces`
- `test_setback_has_6_faces`
- `test_ability_has_8_faces`
- `test_difficulty_has_8_faces`
- `test_proficiency_has_12_faces`
- `test_challenge_has_12_faces`
- `test_boost_face_distribution` — verify exact symbol counts (2 blank, 1 S, 1 SA, 1 AA, 1 A)
- `test_ability_face_distribution` — (1 blank, 2 S, 1 SS, 2 A, 1 SA, 1 AA)
- `test_proficiency_face_distribution` — (1 blank, 2 S, 2 SS, 1 A, 3 SA, 2 AA, 1 Tr)
- `test_challenge_face_distribution` — (1 blank, 2 F, 2 FF, 2 T, 2 FT, 2 TT, 1 De)

---

### [x] 1.2 — Pool Construction Tests

File: `tests/test_dice_roller.py`

Tests for `build_pool(characteristic, skill_ranks, difficulty, boost, setback, upgrades)`.
The pool construction rule is: `max(char, skill)` Ability dice, upgrade `min(char, skill)`
of them to Proficiency dice.

Tests to write:
- `test_pool_untrained_skill` — char=3, skill=0 → 3 Ability, 0 Proficiency
- `test_pool_equal_char_and_skill` — char=2, skill=2 → 0 Ability, 2 Proficiency
- `test_pool_skill_exceeds_char` — char=2, skill=4 → 2 Ability, 2 Proficiency
- `test_pool_char_exceeds_skill` — char=4, skill=2 → 2 Ability, 2 Proficiency
- `test_pool_difficulty_passthrough` — difficulty dice appear unchanged in result
- `test_pool_boost_and_setback` — boost and setback appear unchanged in result
- `test_pool_upgrades_convert_ability_to_proficiency`
- `test_pool_upgrades_cannot_exceed_available_ability_dice`

---

### [x] 1.3 — DiceResult and Symbol Cancellation Tests

File: `tests/test_dice_roller.py`

Tests for the cancellation logic and `DiceResult`. Cancellation rules:
- S cancels F (net determines pass/fail: positive = pass, zero or negative = fail)
- A cancels T (net determines side effects)
- Tr counts as S but does NOT cancel De
- De counts as F but does NOT cancel Tr

Tests to write:
- `test_net_successes_positive_is_pass`
- `test_net_successes_zero_is_fail`
- `test_net_successes_negative_is_fail`
- `test_advantage_threat_cancellation` — 3A + 2T → net 1 Advantage
- `test_triumph_counts_as_success` — 0 S, 1 Tr, 2 F → net -1 successes (fail), 1 Triumph
- `test_despair_counts_as_failure` — 2 S, 1 De → net 1 success (pass), 1 Despair
- `test_triumph_does_not_cancel_despair` — pool with both Tr and De retains both
- `test_despair_does_not_cancel_triumph`
- `test_all_cancel_to_zero` — pass=False, net_successes=0, net_advantage=0

---

### [x] 1.4 — Implement roll_pool()

File: `src/showrunner/tools/dice_roller.py`

After the tests above are written and failing, implement `roll_pool(pool: dict) -> DiceResult`.

Requirements:
- Roll each die in the pool by randomly selecting a face from the appropriate face table
- Accumulate raw symbol counts across all dice in the pool
- Apply cancellation (S vs F, A vs T)
- Triumph and Despair are preserved independently; they also add to raw S and F counts
  before cancellation
- Return a populated `DiceResult`

The function is non-deterministic (uses `random`). Integration tests should mock or seed
random; unit tests for cancellation logic should call the cancellation function directly
(extract it if needed).

---

### [x] 1.5 — Manual Dice Input Parser

File: `src/showrunner/tools/dice_roller.py`

Implement `parse_manual_input(text: str) -> DiceResult`.

Input format: space-separated tokens. Each token is an integer followed by a symbol code.

| Symbol | Code |
|--------|------|
| Success | `s` |
| Failure | `f` |
| Advantage | `a` |
| Threat | `t` |
| Triumph | `tr` |
| Despair | `de` |

Examples:
- `"2s 1a"` → 2 successes, 1 advantage
- `"1tr 2a 1f"` → 1 Triumph, 2 Advantage, 1 Failure (net: 0 successes, Tr preserved)
- `"1de 3t"` → 1 Despair, 3 Threat

Tests to write (in `tests/test_dice_roller.py`):
- `test_parse_simple_successes`
- `test_parse_triumph`
- `test_parse_despair`
- `test_parse_mixed_symbols`
- `test_parse_cancels_correctly` — input that includes both S and F
- `test_parse_invalid_token_raises` — e.g., `"2x"` should raise `ValueError`
- `test_parse_empty_string` — returns all-zero DiceResult

---

## Phase 2 — CrewAI Scaffold

Do not begin Phase 2 until Phase 1 tests are all green.

### 2.1 — Endpoint Connectivity

Before writing any agent code, verify the LAN endpoints are reachable.
Write a minimal connectivity script (not a full test — just a smoke test):

```
tools/check_endpoints.py
```

It should attempt a trivial inference call to each endpoint and print pass/fail.
Use LiteLLM directly; no CrewAI yet.

- Alien: `http://[alien-ip]:8080/v1` (llama.cpp)
- Sardinia: `http://[sardinia-ip]:1234/v1` (LM Studio)
- Gemini: via `GEMINI_API_KEY`

If any endpoint fails, stop and fix before proceeding.

### 2.2 — Agent Implementation

File: `src/showrunner/agents/narrator.py` (and the others)

Implement each agent as a CrewAI `Agent` using the config in `config/agents.yaml`.
Each agent should load its config from the YAML rather than hard-coding strings in Python.

Order of implementation:
1. Narrator (Gemini) — manager agent; implement first, test delegation
2. Referee (Alien) — simplest creative scope; good second test
3. Scribe (Alien) — pure state writes; no creative judgement
4. World Runner (Sardinia)
5. Actors (Sardinia)

### 2.3 — Tool Stubs

Wire the following tool stubs so agents can call them (even if they raise NotImplementedError
for now — the wiring should be correct):

- `consult_narrator(question: str) -> str` — Sardinia/Alien agents escalate to Gemini
- `ask_player(question: str) -> str` — blocks on CLI input from Tom
- `roll_dice(pool: dict) -> DiceResult` — wraps `dice_roller.roll_pool()` (Phase 1 done)
- `read_state(file: str) -> dict` — wraps `state_reader`
- `write_state(file: str, updates: dict)` — wraps `state_writer`

### 2.4 — Basic Turn Loop

File: `src/showrunner/orchestrator.py`

Implement a minimal turn loop that:
1. Calls Narrator to assess scene
2. Calls World Runner to narrate
3. Prompts CLI for player input (or calls Actors for AI character)
4. Calls Referee
5. Calls Scribe

No game content required — just verify the message flow works end-to-end with placeholder
tasks.

---

## Phase 3 — State Management

Do not begin Phase 3 until Phase 2 agents can communicate end-to-end.

### 3.1 — State Reader

File: `src/showrunner/tools/state_reader.py`

Implement the three load functions. Use `pyyaml` for YAML files.

Tests to write (in `tests/test_state_reader.py`):
- `test_load_character_returns_dict`
- `test_load_character_has_required_keys` — identity, characteristics, skills, status
- `test_load_scene_state`
- `test_load_party_stats`
- `test_load_missing_file_raises`

Use fixture YAML files in `tests/fixtures/` for tests — do not read from `characters/` or
`state/` in tests.

### 3.2 — State Writer

File: `src/showrunner/tools/state_writer.py`

Implement the three write functions.

Tests to write (in `tests/test_state_writer.py`):
- `test_update_party_stats_writes_yaml`
- `test_update_party_stats_merges_not_replaces` — existing keys not in `updates` are preserved
- `test_append_session_log_creates_if_missing`
- `test_append_session_log_appends_not_overwrites`
- `test_update_scene_state`

Use `tmp_path` (pytest fixture) for all file writes in tests.

### 3.3 — render_actor_prompt

File: `src/showrunner/agents/actors.py`

Implement `render_actor_prompt(character_yaml: dict, persona_md: str, scene_state: dict) -> str`.

The output is a string containing the full system prompt for the Actors agent.
Sort order is defined in `docs/plans/character_schema.md` (section "render_actor_prompt — Output Order").

Tests to write (in `tests/test_render_actor_prompt.py`):
- `test_output_contains_character_name`
- `test_static_content_appears_before_dynamic` — check that persona text precedes wounds/strain
- `test_skills_rendered_with_descriptors` — descriptor field appears, not raw rank number
- `test_active_critical_injuries_included`
- `test_no_critical_injuries_section_is_clean` — empty list renders gracefully
- `test_scene_plan_included_when_present`
- `test_scene_plan_absent_when_missing` — no KeyError if scene plan not in scene_state

---

## Phase 4 — MVP Scene

Do not begin Phase 4 until Phase 3 state management is tested and working.

**Phases 5 and 6 are not required for Phase 4.** The Referee uses inline rules for the
Bargos mansion scene. `rules_lookup()` stays stubbed. NPC stats live in the scene YAML.

Full brief is in `architect_todo.md` Phase 4. The programmer's job here is execution:
convert the architect's scene design into running code and play the scene.

At the start of Phase 4, the architect should have provided:
- At least one PC character YAML + MD in `characters/`
- Scene YAML format specification
- Bargos mansion scenes converted to YAML (`state/scene_0.yaml`, `state/scene_1.yaml`)
  - Scene YAMLs include inline Gamorrean guard stats (no OggDude lookup needed)

### Referee in Phase 4

The Referee's system prompt for this scene must include inline:
- Pool construction rule (already in `dice_roller.py` comments — copy to prompt)
- Vigilance check: Average difficulty (2 purple), opposed by Stealth if Gamorreans are hiding
- Brawl/Melee combat: difficulty = target's defense rating, +1 purple per range band beyond engaged
- Soak: damage - soak = wounds taken (minimum 0)
- Critical injuries: triggered on Advantage spend or when wounds exceed threshold

Do NOT wire `rules_lookup()` in Phase 4. Leave it raising `NotImplementedError`.

### What to do when you hit an issue

Issues found during play are bugs — fix them. If something requires an architectural
decision, document it and raise it with Tom before implementing a workaround.

---

## Phase 5 — Genesys Rules Parser

Do not begin Phase 5 until Phase 4 has been played through successfully.

This phase delivers the data that `rules_lookup()` queries. It unblocks Phase 7.

- [ ] Write a PDF extraction script: `tools/parse_rulebook.py`
  - Input: `docs/references/Genesys_Core_Rulebook.pdf`
  - Output: section files in `swskin/rules/` (dice.md, combat.md, skills.md, talents.md)
  - Use `pymupdf` (already installed)
- [ ] Write `swskin/rules/index.md` — section list with page references
- [ ] Implement `rules_lookup(keyword: str) -> str` in `src/showrunner/tools/rules_lookup.py`
  - Keyword search against indexed sections; returns most relevant section text
- [ ] Wire `rules_lookup()` into the Referee agent
- [ ] Smoke test: Referee can retrieve the correct rule for "critical injury", "soak", "Brawl"

---

## Phase 6 — OggDude Data Ingestion

Do not begin Phase 6 until Phase 5 is complete.

This phase replaces inline NPC stats with a proper data source for Phase 7.

- [ ] Write `tools/xml_to_md.py` — convert OggDude XML exports to structured Markdown
- [ ] Output to `swskin/data/`: `weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Smoke test: Referee can look up Gamorrean vibro-ax damage, crit, range, special from `weapons.md`
