# Terminology

Canonical terms for the showrunner engine. Use these consistently across all code,
docs, and comments. When in doubt, come here first.

---

## People

| Term | Definition |
|------|-----------|
| **User** | A human sitting at the keyboard. The person playing the game. |
| **PC** (Player Character) | The character(s) directly controlled by the User via CLI. `player: "human"` in character YAML. |
| **Companion** | A party character driven by AI (Actors agent), but taking major direction from the User through natural language. `player: "companion"` in character YAML. |
| **NPC** (Non-Player Character) | Any character driven entirely by the Show Runner and plot logic. No `player` field in character YAML. |

**Party** = all PCs and Companions together. NPCs are not party members even if they
travel with the group.

---

## Narrative Structure

| Term | Definition |
|------|-----------|
| **Session** | One continuous play session from startup to quit. |
| **Scene** | A self-contained event at a location, loaded from a scene YAML file. |
| **Beat** | A dramatic sub-unit within a scene with a specific purpose and exit condition. |
| **Turn** | One full pass through all steps in the game loop. |

A beat spans one or more turns. A scene spans one or more beats.

---

## Agents

| Term | Definition |
|------|-----------|
| **Show Runner** | The GM-brain agent. Plans beats, identifies checks, rules on outcomes. |
| **Narrator** | The GM-voice agent. Delivers scene prose, beat openers, last-action extraction. |
| **Actors** | The voicing agent. Plays both NPCs and Companions. |
| **Scribe** | The record-keeping agent. Writes one-sentence session log entries. |

---

## Character `player` Field Values

| Value | Character type | Who drives it |
|-------|---------------|--------------|
| `"human"` | PC | User via CLI |
| `"companion"` | Companion | Actors agent, direction from User |
| *(omitted)* | NPC | Show Runner / plot |
