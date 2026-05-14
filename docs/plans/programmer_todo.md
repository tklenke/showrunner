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

### [x] 4.34 — Route pipeline-internal calls to Scribe agent

Per game_loop.md Ref A, the following `call_llm` calls must change agent:

- `run_companion_wave` — narrator summary call → `"scribe"`
- `run_npc_wave` — narrator summary call → `"scribe"`
- `run_summaries` — narrator call → `"scribe"`
- `run_checks` — show_runner call → `"referee"`
- `run_narrative` — show_runner call → `"narrator"`
- `run_last_actions` — narrator call → `"scribe"`
- `run_plan_update` — individual plan calls → `"scribe"`

Agent prompt files to create/update:
- Scribe: new `config/prompts/agent_scribe.md` — compact summarization, last-action
  extraction, and per-character plan generation (pipeline-internal). Add `prompt_file`
  to `agents.yaml`. Remove old state-writer goal/backstory.
- Referee: already has goal/backstory in `agents.yaml`; wire up `prompt_file` if needed.

Follow TDD. Update `test_runner.py` assertions that check `call_llm` agent names.

The following tests now fail due to config changes and must be updated to reflect current
model assignments (all agents now on gemini) and the referee/scribe prompt_file path:

- `test_config.py`: `test_show_runner_uses_sardinia`, `test_narrator_uses_sardinia_endpoint`,
  `test_referee_uses_alien_endpoint`, `test_scribe_uses_alien_endpoint`,
  `test_actors_uses_sardinia_endpoint` — assertions reference old local model endpoints;
  update to assert gemini model is used.
- `test_llm.py`: `test_call_llm_passes_model_from_config`,
  `test_call_llm_passes_api_base_for_local_models` — narrator now routes to gemini, not
  sardinia; update accordingly.
- `test_llm.py`: `test_call_llm_non_gemini_does_not_include_thinking` — narrator is now
  gemini; pick a genuinely non-gemini agent or use a fake config.
- `test_llm.py`: `test_build_system_prompt_referee_fallback_contains_role` — referee now
  has a `prompt_file`; the fallback path no longer applies. Delete or replace this test.

---

### [ ] 4.35 — Manual Dice Input Parser

Implement `parse_dice_input(text: str) -> dict` in `src/showrunner/dice.py`.

Format (from game_loop.md Step 6): single-letter keys with integer counts, case-insensitive,
spaces tolerated. Valid keys: S=Success, A=Advantage, T=Triumph, F=Failure, H=Threat, D=Despair.
Unknown letters are ignored with a warning logged. Returns a dict of symbol→count.

Examples:
- `"S2A1"` → `{"success": 2, "advantage": 1}`
- `"S2 A1 T1"` → `{"success": 2, "advantage": 1, "triumph": 1}`
- `"f1h2d1"` → `{"failure": 1, "threat": 2, "despair": 1}`

Wire into the orchestrator at Step 6 when manual dice input is requested.

Follow TDD.

---

### [ ] 4.36 — Context Window Pre-flight Check

Add `max_context_tokens` (integer) to each agent entry in `config/agents.yaml`.
In `call_llm()` in `llm.py`, before calling `litellm.completion`, estimate the prompt
token count (`len(system + user) // 4`) and log a warning if it exceeds the agent's
`max_context_tokens`. Do not abort — warn only, so play continues.

Reasonable starting values (can be tuned):
- gemini/gemini-2.5-flash: 1_000_000
- sardinia/llama-3.1-8b: 8_192
- alien models: 8_192

Follow TDD. The warning must be captured and asserted in tests (per project testing standards).

---

### [ ] 4.37 — Inline NPC stats, minion group stats, and pronoun support

Fixes two known issues (architect_todo): inline NPCs invisible to `_build_char_stats`,
and inline NPCs entering the NPC wave with no name or mechanical context.

---

#### A — Data: scene_0.yaml and character YAMLs

Add `pronoun` to `identity` in every character YAML under `skin/characters/`:
- `bargos_the_hutt.yaml`: `pronoun: "he"`
- `kaelen_sunara.yaml`: `pronoun: "she"`
- `z4p0.yaml`: `pronoun: "it"`
- any others present

Update `skin/scenes/scene_0.yaml` inline_npcs to add `pronoun` and flat stats block.
Stats shape mirrors `minion_groups` (characteristics/skills/derived at top level, no
wrapper key). Stats are optional — omit for purely atmospheric NPCs.

```yaml
inline_npcs:
  - id: "c3p9"
    name: "C3-P9"
    pronoun: "it"
    role: "Bargos's protocol droid; delivers messages, facilitates introductions"
    key_traits: "Deferential, precise, genuinely loyal to Bargos. Speaks in complete
      sentences. Slightly condescending to organics in a polite, oblivious way."
    characteristics:
      brawn: 1
      agility: 1
      intellect: 3
      cunning: 2
      willpower: 2
      presence: 3
    skills:
      - name: Charm
        ranks: 2
      - name: Negotiation
        ranks: 1
      - name: Knowledge (Outer Rim)
        ranks: 2
    derived:
      wound_threshold: 11
      strain_threshold: 10
      soak: 2
  - id: "genko"
    name: "Genko"
    pronoun: "he"
    role: "Bargos's Toydarian aide; whispers counsel, manages logistics"
    key_traits: "Furtive, anxious, speaks in a rapid Toydarian-accented Basic. Knows
      more than he lets on about the Gavos situation. Visibly uncomfortable when
      the subject of the mine comes up."
    characteristics:
      brawn: 1
      agility: 2
      intellect: 3
      cunning: 3
      willpower: 2
      presence: 2
    skills:
      - name: Deception
        ranks: 2
      - name: Negotiation
        ranks: 1
      - name: Streetwise
        ranks: 1
    derived:
      wound_threshold: 11
      strain_threshold: 12
      soak: 1
```

Add `pronoun: "they"` to the `gamorrean_guards` entry in `minion_groups`.

---

#### B — `actors.py`: `render_inline_npc_prompt(npc: dict) -> str` (new function)

Replace the bare `npc["key_traits"]` string in `load_scene_characters` with a rendered
prompt built by this new function. Output format:

```
# {name}
Pronouns: {pronoun}
Role: {role}
{key_traits}

## Characteristics                          ← only if characteristics present
Brawn {n} | Agility {n} | ...

## Skills                                   ← only if skills present
- {Skill} rank {n}
...
```

`load_scene_characters` calls `render_inline_npc_prompt(npc)` for every inline NPC
instead of `npc["key_traits"]`.

---

#### C — `actors.py`: `render_actor_prompt` — add pronoun

Add one line to the identity block (position 1, after name/species line):

```
Pronouns: {pronoun}
```

Read from `identity.get("pronoun", "they")`. Default `"they"` if absent.

---

#### D — `orchestrator.py`: extend `_build_char_stats` coverage

`_build_char_stats(yamls)` currently only processes characters from `load_scene_yamls`
(full YAML files). Extend the orchestrator to also build stats for:

1. **Inline NPCs with stats** — iterate `scene.get("inline_npcs", [])`. For each that
   has a `characteristics` key, construct a minimal YAML-shaped dict and pass it through
   `_build_char_stats`. Set `identity.name` from `npc["name"]`.

2. **Minion groups** — iterate `scene.get("minion_groups", [])`. Each already has
   `characteristics` and `skills` at the top level. Same approach.

Merge all three into a single `char_stats` dict before passing to `run_checks`.
Do not change `_build_char_stats` itself — normalise the input dicts in the caller.

---

#### E — `orchestrator.py` + `runner.py` + task prompt: pronoun map into `run_narrative`

Build a pronoun map in the orchestrator from all character sources:
- Full YAML characters: `identity.pronoun`
- Inline NPCs: `npc["pronoun"]`
- Minion groups: `group.get("pronoun", "they")`
- Human PC: from YAML `identity.pronoun`

Format as a small block, e.g.:
```
Bargos: he | Kaelen: she | Z-4P0: it | Genko: he | C3-P9: it | Renegade Gamorrean Guards: they
```

Add `pronoun_map: str = ""` parameter to `run_narrative()` in `runner.py`.
Add `{pronoun_map}` placeholder to `config/prompts/task_run_narrative.md` under a
`## Character Pronouns` header. Pass the map from the orchestrator's `run_narrative` call.

`run_beat_opener` does not need the pronoun map.

---

Follow TDD throughout. All four code changes need tests before implementation.

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
