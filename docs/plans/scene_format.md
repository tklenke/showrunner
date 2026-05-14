# Adventure Scene Format

Static authored content for each scene in the adventure. These files are read by agents at
the start of a scene and do not change during play. Runtime state lives in `scene_state.yaml`.

Scenes are numbered sequentially: `state/scene_0.yaml`, `state/scene_1.yaml`, etc.

---

## Distinction: Scene Files vs. Runtime State

| File | Content | Written by |
|------|---------|-----------|
| `state/scene_N.yaml` | Authored adventure content — beats, NPC roster, read-aloud text, encounter stats | Architect (static) |
| `state/scene_state.yaml` | Current runtime state — active scene, current beat, ticking clocks, character plans | Scribe (dynamic) |

The Scribe never writes to scene files. Agents load a scene file once at scene start and
hold it in context for the duration.

---

## Schema

```yaml
scene_id: string          # unique slug, e.g. "bargos_audience"
title: string             # human-readable display name

location:
  name: string            # e.g. "Bargos's Throne Room, Sleheyron"
  atmosphere: string      # 1-3 sentence mood description for World Runner
  read_aloud: |           # Opening narration; World Runner delivers this verbatim on scene entry

characters_present:             # List of character file stems in characters/
  - string                # e.g. "bargos_the_hutt" → characters/bargos_the_hutt.yaml + .md

inline_npcs:              # Minor NPCs not worth a full character file
  - id: string            # reference id used in beats
    name: string
    role: string          # brief description of their function in the scene
    key_traits: string    # voice/manner notes for Actors agent

minion_groups:            # Combat-only inline stat blocks for minion-tier enemies
  - id: string
    name: string
    count: int
    characteristics:
      brawn: int
      agility: int
      intellect: int
      cunning: int
      willpower: int
      presence: int
    skills:               # flat map: skill_name: ranks (only combat-relevant skills needed)
      skill_name: int
    soak: int
    wound_threshold: int  # per minion; group dies at multiples of this
    weapons:
      - name: string
        skill: string     # e.g. "Melee", "Brawl", "Ranged (Light)"
        damage: int       # final computed value (characteristic already added if applicable)
        critical: int
        range: string     # Engaged | Short | Medium | Long | Extreme
        special: string   # optional: "Vicious 2", "Pierce 1", etc.

beats:                    # Ordered narrative events; Narrator decides when each fires
  - id: string
    title: string
    trigger: string       # Condition for Narrator to evaluate (natural language)
    narrator_notes: |     # GM-brain context: NPC agendas, how to run this beat, what matters
    world_runner_notes: | # Atmosphere and narration cues for prose delivery
    checks:               # Skill checks the Referee may call for in this beat
      - skill: string
        characteristic: string
        difficulty: int         # number of difficulty (purple) dice
        opposed_skill: string   # omit if not opposed
        notes: string           # special circumstances or consequences

exit:
  condition: string       # Natural language; Narrator evaluates
  next_scene: string      # scene_id of next scene, or null if final scene
```

---

## Narrator Prompt Assembly (Cache-Aware)

The scene file is the Narrator's **static context block** — loaded once when the scene
starts, placed high in the prompt where it caches across every turn of the scene.
Dynamic runtime state goes at the bottom and re-renders each turn.

This follows the same principle as `render_actor_prompt()`: most-static at top,
most-volatile at bottom.

```
┌─────────────────────────────────────────────────┐
│  Narrator system prompt (role, responsibilities) │  ← never changes
├─────────────────────────────────────────────────┤
│  Scene file content (scene_N.yaml)               │  ← static for scene duration
│    location, atmosphere                          │    loaded once on scene entry
│    characters_present + inline_npcs                   │    sits in prompt cache
│    minion_groups (if any)                        │
│    full beats list (reference material)          │
├─────────────────────────────────────────────────┤
│  Current beat id + character scene plans         │  ← changes each beat
│    from scene_state.yaml                         │
├─────────────────────────────────────────────────┤
│  Party stats (wounds, strain)                    │  ← changes each action
│    from party_stats.yaml                         │
├─────────────────────────────────────────────────┤
│  Ticking clock status                            │  ← changes on each clock event
│    from scene_state.yaml                         │
├─────────────────────────────────────────────────┤
│  Last player action                              │  ← changes every turn
└─────────────────────────────────────────────────┘
```

**Why this matters:** The Narrator is called every turn. Everything above the dynamic
section is identical call-to-call within a scene. Prefix caching on Gemini means the
static block is only billed once per scene rather than once per turn.

### render_narrator_context()

A function in `src/showrunner/agents/narrator.py` (analogous to `render_actor_prompt()`):

```python
def render_narrator_context(
    scene: dict,
    scene_state: dict,
    party_stats: dict,
    last_action: str,
) -> str:
```

Returns a single string in cache-friendly order. The Programmer passes this as the
task description to the Narrator agent each turn.

---

## Implementation Notes

### Loading

`state_reader.py` needs a `load_adventure_scene(n: int) -> dict` function:

```python
def load_adventure_scene(n: int, state_dir: str = "state") -> dict:
    path = Path(state_dir) / f"scene_{n}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)
```

### Agent Usage

- **Narrator**: Receives the full scene dict as context. Uses `beats` to manage pacing,
  `characters_present` to know who is available, `exit` to decide when to transition.
- **World Runner**: Uses `location.read_aloud` at scene entry. Uses `world_runner_notes`
  in beats for atmosphere cues during narration.
- **Actors**: Uses `characters_present` list to know which characters to voice.
  `render_actor_prompt()` is called per character using the character file.
  `inline_npcs` provides voice notes for minor characters.
- **Referee**: Uses `beats[*].checks` for difficulty guidance and `minion_groups` for
  enemy stats in combat.

### Runtime State Updates

When Scribe transitions to a new beat, it writes to `scene_state.yaml`:

```yaml
current_scene: 0           # scene_N.yaml number
current_beat: "audience"   # beat id
ticking_clocks: []
character_plans: {}
```

---

## Minion Group Mechanics Reference

**Pool construction for a minion group attack:**
- skill_ranks = listed rank (stays constant regardless of group size)
- characteristic = relevant characteristic from the `characteristics` block
- Apply pool construction: `max(char, skill)` Ability, upgrade `min(char, skill)` to Proficiency

**Wound tracking:**
- Group takes damage as a pool; individual minions die at multiples of `wound_threshold`
- Count living minions: `ceil(remaining_wounds / wound_threshold)`
- Skill ranks do not decrease as minions die (they represent the group's trained ability)

**Defense:**
- Minion groups have no active defense; they soak damage with their `soak` value
- Add difficulty dice per range band beyond Engaged for ranged attacks
