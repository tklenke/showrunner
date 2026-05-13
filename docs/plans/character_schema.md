# Character Sheet Schema

Character sheets are YAML files stored in `swskin/characters/[name].yaml`.
The `player` field controls who drives the character: `"human"` = User-controlled via CLI, `"companion"` = Actors agent drives as a party Companion, omitted/null = NPC driven entirely by Show Runner/plot.

```yaml
identity:
  name: string               # character's full name
  species: string            # e.g. "Human", "Twi'lek", "Rodian"
  career: string             # e.g. "Smuggler", "Hired Gun", "Explorer"
  specialization: string     # e.g. "Pilot", "Mercenary Soldier"
  player: "human" | "companion"   # omit for NPC
  obligation:
    amount: int              # total obligation value
    type: string             # e.g. "Debt", "Bounty", "Family"
    details: string          # narrative description
  motivation:
    type: string             # e.g. "Ambition", "Cause", "Relationship"
    details: string
  background: string         # narrative backstory

characteristics:
  brawn: int        # 1–5: physical power, toughness
  agility: int      # 1–5: dexterity, reflexes
  intellect: int    # 1–5: intelligence, education
  cunning: int      # 1–5: shrewdness, deceptiveness
  willpower: int    # 1–5: discipline, mental fortitude
  presence: int     # 1–5: charisma, leadership

derived:
  wound_threshold: int   # brawn + species base (humans: brawn + 10)
  strain_threshold: int  # willpower + species base (humans: willpower + 10)
  soak: int              # brawn + any armor soak bonus
  defense:
    melee: int           # usually 0 unless armor/talent provides it
    ranged: int

skills:
  - name: string
    characteristic: string   # the linked characteristic (e.g. "Agility")
    ranks: int               # 0–5 trained ranks
    career: bool             # true = career skill (half XP cost)
    descriptor: string       # natural language for render_actor_prompt (e.g. "your strongest suit")

talents:
  - name: string
    ranks: int               # for ranked talents; 1 for non-ranked
    description: string      # brief mechanical effect

equipment:
  weapons:
    - name: string
      skill: string          # e.g. "Ranged (Light)", "Melee"
      damage: int
      critical: int
      range: string          # Engaged, Short, Medium, Long, Extreme
      encumbrance: int
      special: string        # optional: "Stun Setting", "Pierce 2", etc.
  armor:
    - name: string
      defense: int           # ranged/melee defense granted
      soak_bonus: int        # added to brawn for total soak
      encumbrance: int
  gear:
    - name: string
      encumbrance: int       # optional
      quantity: int          # optional, defaults to 1

resources:
  credits: int
  encumbrance_threshold: int   # brawn + 5 for most species

# --- Updated by Scribe during play; do not edit manually ---
status:
  wounds: 0
  strain: 0
  critical_injuries: []        # list of active critical injury names
```

## render_actor_prompt — Output Order

The renderer assembles the Actors agent's full context by combining the persona file
and a dynamically generated mechanical summary. **Sort from most static to least static**
so the stable content sits at the top of the prompt where it caches and where the model
weights it most heavily. Volatile state at the bottom gets re-evaluated every call.

Render order (top → bottom):

1. **Name, species, career** — identity never changes
2. **Persona file content** (`[name].md`) — personality, voice, backstory, motivations, relationships
3. **Characteristics** — change only with rare advancement (between sessions at earliest)
4. **Skills with descriptors** — change only when XP is spent between sessions
5. **Talents** — same cadence as skills
6. **Base derived stats** — wound/strain thresholds, soak, defense (change only with advancement)
7. **Equipment** — changes during play (items used, lost, or found)
8. **Credits** — changes frequently during play
9. **Current scene plan** — from `scene_state.yaml`; changes when the character reassesses their approach, but typically stable across several turns
10. **Active critical injuries** — acquired during play; persists until treated
11. **Current wounds / strain** — most volatile; can change every combat round

The dividing line between "cached" and "re-evaluated" falls roughly between item 6 and 7.
Everything above that line should be identical call-to-call unless the session ended and
XP was spent. Everything below can change within a single scene.

The renderer is a deterministic Python function — not an LLM call. Fast, cheap, testable.
The `descriptor` field on each skill (`"your strongest suit"`) is what lets it produce
natural language rather than raw numbers.

## Pool Construction (for reference)

Given `characteristic` value and `skill_ranks`:
- Take `max(characteristic, skill_ranks)` Ability dice (d8, green)
- Upgrade `min(characteristic, skill_ranks)` of them to Proficiency dice (d12, yellow)
- Add Difficulty dice (d8, purple) per check difficulty level
- Add Boost/Setback dice per situational modifiers

## Species Base Stats (common species)

| Species | Wound Base | Strain Base | Starting Characteristics |
|---------|-----------|-------------|--------------------------|
| Human | +10 | +10 | All 2 |
| Twi'lek | +10 | +11 | Cunning 3, Presence 3, Brawn 1, others 2 |
| Rodian | +10 | +10 | Agility 3, Cunning 3, Brawn 1, others 2 |
| Wookiee | +14 | +8 | Brawn 3, Agility 2, others 2 |
