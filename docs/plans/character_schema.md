# Character Sheet Schema

Character sheets are YAML files stored in `swskin/characters/[name].yaml`.
The `player` field controls who drives the character: `"human"` prompts Tom via CLI, `"ai"` lets the Actors agent run the character.

```yaml
identity:
  name: string               # character's full name
  species: string            # e.g. "Human", "Twi'lek", "Rodian"
  career: string             # e.g. "Smuggler", "Hired Gun", "Explorer"
  specialization: string     # e.g. "Pilot", "Mercenary Soldier"
  player: "human" | "ai"
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
