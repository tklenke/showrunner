# ABOUTME: Actors agent — voices NPCs with decisions, dialogue, and physical responses.
# ABOUTME: Runs on Sardinia (Llama 3.1 8B); receives rendered character prompt from render_actor_prompt().

# TODO(Phase 2): Implement CrewAI Agent and render_actor_prompt() Python renderer.


def render_actor_prompt(character_yaml: dict, persona_md: str, scene_state: dict) -> str:
    """Build the full system prompt for an NPC actor.

    Sorts content from most static (identity, persona) to most volatile (wounds, strain)
    to maximize prompt cache reuse across turns.
    """
    raise NotImplementedError


class Actors:
    """Placeholder for the Actors agent (Sardinia)."""
    pass
