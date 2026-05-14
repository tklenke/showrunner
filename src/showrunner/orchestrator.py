# ABOUTME: Main turn loop — five-step resolution pipeline per turn.
# ABOUTME: Phase 1: NPC wave. Phase 2: PC wave. Phase 3a-e: resolution pipeline.

import logging
from datetime import datetime
from pathlib import Path

_log = logging.getLogger(__name__)

from showrunner.agents.actors import _active_npc_ids, load_scene_characters, load_scene_yamls, render_actor_beat_context
from showrunner.agents.narrator import render_narrator_context
from showrunner.agents.show_runner import render_show_runner_context
from showrunner.config import apply_litellm_settings, load_agent_configs
from showrunner.instrumentation import setup_instrumentation
from showrunner.llm import build_system_prompt, call_llm, load_yaml_task_prompt
from showrunner.runner import (
    run_beat_opener,
    run_last_actions,
    run_npc_wave,
    run_narrative,
    run_companion_wave,
    run_plan_update,
    run_rulings,
    run_summaries,
    run_checks,
)
from showrunner.tools.dice_roller import roll_pool
from showrunner.tools.state_reader import load_party_stats, load_scene_state
from showrunner.tools.state_writer import advance_beat, initialize_npc_stats, initialize_scene_state, update_party_stats, update_scene_state

# Difficulty name → number of difficulty dice
_DIFFICULTY_MAP = {
    "Easy": 1,
    "Average": 2,
    "Hard": 3,
    "Daunting": 4,
    "Formidable": 5,
}


def _setup_session_log(timestamp: str) -> logging.Logger:
    """Set up a session log that writes to logs/session_TIMESTAMP.log."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / f"session_{timestamp}.log"

    logger = logging.getLogger("showrunner.session")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(file_handler)

    logger.info(f"Session log: {log_path}")
    return logger


def is_human_character(character_yaml: dict) -> bool:
    """Return True if this character is driven by the human player."""
    return character_yaml.get("identity", {}).get("player") == "human"


def _find_human_pc_name(scene: dict, characters_dir: str = "skin/characters") -> str:
    """Return identity.name of the human player character in this scene, or 'Player'."""
    import yaml as pyyaml
    from pathlib import Path
    for name in scene.get("characters_present", []):
        yaml_path = Path(characters_dir) / f"{name}.yaml"
        try:
            with open(yaml_path) as f:
                char_yaml = pyyaml.safe_load(f)
            if is_human_character(char_yaml):
                return char_yaml["identity"].get("name", name)
        except FileNotFoundError:
            continue
    return "Player"


_DIVIDER = "─" * 60


def prompt_player_action(character_name: str) -> str:
    """Prompt the CLI for the human player's action and return their input."""
    print(f"\n{_DIVIDER}")
    return input(f"  What do you and your companions do? > ")


def _next_beat_id(scene: dict, current_beat_id: str) -> str | None:
    """Return the id of the beat after current_beat_id, or None if last."""
    beats = scene.get("beats", [])
    ids = [b["id"] for b in beats]
    try:
        idx = ids.index(current_beat_id)
        return ids[idx + 1] if idx + 1 < len(ids) else None
    except ValueError:
        return None


def _beat_prompt(scene: dict, current_beat_id: str) -> str:
    """Prompt for beat advancement; returns 'stay', 'advance', a beat ID, or 'quit'."""
    beats = scene.get("beats", [])
    beat_ids = [b["id"] for b in beats]
    next_id = _next_beat_id(scene, current_beat_id)

    print(f"\n{_DIVIDER}")
    print(f"  Beat: {current_beat_id}  ({' → '.join(beat_ids)})")
    if next_id:
        prompt = f"  [Enter] stay  |  [a] advance to '{next_id}'  |  [beat ID] jump  |  [q] quit > "
    else:
        prompt = f"  Last beat.  [Enter] stay  |  [beat ID] jump  |  [q] quit > "
    choice = input(prompt).strip().lower()
    if choice == "":
        return "stay"
    if choice == "a" and next_id:
        return "advance"
    return choice


def _parse_check_specs(review_output: str) -> list[dict]:
    """Parse the Show Runner review output into a list of check spec dicts.

    Expects either "NO_CHECKS" or a CHECKS:/CHECKS_END block:
        CHECKS:
        1. actor | skill | characteristic | difficulty | notes
        CHECKS_END
    """
    if "NO_CHECKS" in review_output:
        return []
    specs = []
    in_checks = False
    for line in review_output.splitlines():
        stripped = line.strip()
        if "CHECKS:" in stripped:
            in_checks = True
            continue
        if "CHECKS_END" in stripped:
            break
        if in_checks and stripped and stripped[0].isdigit():
            content = stripped.split(".", 1)[1].strip() if "." in stripped else stripped
            parts = [p.strip() for p in content.split("|")]
            if len(parts) >= 4:
                specs.append({
                    "actor": parts[0],
                    "skill": parts[1],
                    "characteristic": parts[2],
                    "difficulty": parts[3],
                    "notes": parts[4] if len(parts) > 4 else "",
                })
    return specs


def _parse_ruling_specs(text: str) -> list[dict]:
    """Parse Phase 3b check output into ruling spec dicts.

    Expected format per line:
        {n}. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}
    Returns [] for "NO_CHECKS" or unrecognised input.
    """
    if "NO_CHECKS" in text:
        return []
    specs = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or not stripped[0].isdigit():
            continue
        content = stripped.split(".", 1)[1].strip() if "." in stripped else stripped
        parts = [p.strip() for p in content.split("|")]
        if len(parts) < 4:
            continue
        # "Presence 2" → characteristic="Presence", char_value=2
        char_parts = parts[2].rsplit(None, 1)
        characteristic = char_parts[0] if char_parts else parts[2]
        try:
            char_value = int(char_parts[1]) if len(char_parts) > 1 else 0
        except ValueError:
            char_value = 0
        try:
            skill_rank = int(parts[3])
        except ValueError:
            skill_rank = 0
        specs.append({
            "actor": parts[0],
            "skill": parts[1],
            "characteristic": characteristic,
            "char_value": char_value,
            "skill_rank": skill_rank,
            "difficulty": parts[4] if len(parts) > 4 else "",
            "notes": parts[5] if len(parts) > 5 else "",
        })
    return specs


def _ruling_specs_parser(raw: str) -> tuple[list[dict], bool]:
    """parse_structured-compatible parser for run_checks output.

    Returns (specs, ok). ok is True for NO_CHECKS (valid empty result) or when
    at least one spec parses successfully. False means malformed output.
    """
    if "NO_CHECKS" in raw:
        return [], True
    specs = _parse_ruling_specs(raw)
    return specs, len(specs) > 0


_CHECK_PYTHON_SAMPLE = (
    "# One numbered pipe-delimited line per check:\n"
    "1. Bargos | Negotiation | Presence 4 | 2 | Average | vs. Docking Authority\n"
    "2. Kaelen | Perception | Cunning 3 | 1 | Hard | \n"
    "\n"
    "# Or if no checks are needed:\n"
    "NO_CHECKS"
)


def _build_char_stats(
    yamls: dict[str, dict],
    inline_npcs: list[dict] | None = None,
    minion_groups: list[dict] | None = None,
) -> dict[str, str]:
    """Format character stats from raw YAML dicts into per-character strings.

    Also accepts inline_npcs and minion_groups (flat dicts from scene YAML).
    Inline NPCs without characteristics are skipped (they have no check-relevant stats).
    """
    def _format_entry(char_id: str, name: str, chars: dict, skills: list) -> str:
        char_str = ", ".join(
            f"{k.capitalize()} {v}" for k, v in chars.items() if isinstance(v, int)
        )
        skill_str = ", ".join(
            f"{s['name']} rank {s.get('ranks', 1)}" for s in skills
        ) if skills else "none"
        lines = [f"### {name}"]
        if char_str:
            lines.append(f"Characteristics: {char_str}")
        lines.append(f"Skills: {skill_str}")
        return "\n".join(lines)

    result: dict[str, str] = {}

    for char_id, yaml in yamls.items():
        name = yaml.get("identity", {}).get("name", char_id)
        result[char_id] = _format_entry(
            char_id, name,
            yaml.get("characteristics", {}),
            yaml.get("skills", []),
        )

    for npc in (inline_npcs or []):
        if not npc.get("characteristics"):
            continue
        result[npc["id"]] = _format_entry(
            npc["id"], npc.get("name", npc["id"]),
            npc.get("characteristics", {}),
            npc.get("skills", []),
        )

    for group in (minion_groups or []):
        result[group["id"]] = _format_entry(
            group["id"], group.get("name", group["id"]),
            group.get("characteristics", {}),
            group.get("skills", []),
        )

    return result


def _parse_summaries_log(path) -> dict[str, str]:
    """Parse a summaries log file into {actor: summary} dict."""
    if not Path(path).exists():
        return {}
    result: dict[str, str] = {}
    for line in Path(path).read_text().splitlines():
        if ": " in line:
            actor, summary = line.split(": ", 1)
            result[actor.strip()] = summary.strip()
    return result


def parse_structured(raw: str, parser, *, context: str = "", python_sample: str = "") -> tuple:
    """Parse raw LLM output, escalating through a repair chain on failure.

    parser(raw) -> (result, ok: bool). Returns (result, recovered: bool).
    Steps: direct parse → Scribe → User+Scribe → zero fallback.
    """
    result, ok = parser(raw)
    if ok:
        return result, False

    repair_msg = load_yaml_task_prompt("repair_structured", raw=raw, context=context, python_sample=python_sample)
    fixed = call_llm("scribe", build_system_prompt("scribe"), repair_msg)
    result, ok = parser(fixed)
    if ok:
        return result, True

    # User prompt → Scribe interprets
    try:
        user_input = input("Parse failed. Enter correction (or press Enter to skip): ").strip()
    except (EOFError, OSError):
        user_input = ""
    if user_input:
        user_msg = load_yaml_task_prompt("repair_structured", raw=user_input, context=context, python_sample=python_sample)
        fixed = call_llm("scribe", build_system_prompt("scribe"), user_msg)
        result, ok = parser(fixed)
        if ok:
            return result, True

    # Zero fallback
    _log.warning(f"parse_structured failed for context: {context!r}. Using zero fallback.")
    return result, False


def _apply_beat_notes(beat: dict, sr_ctx: str, narrator_ctx: str) -> tuple[str, str]:
    """Append beat-specific director notes to the SR and Narrator context strings."""
    sr_notes = beat.get("show_runner_notes", "")
    narrator_notes = beat.get("narrator_notes", "")
    if sr_notes:
        sr_ctx += f"\n\n## Beat Director Notes:\n{sr_notes}"
    if narrator_notes:
        narrator_ctx += f"\n\n## Beat Director Notes:\n{narrator_notes}"
    return sr_ctx, narrator_ctx


def _read_last_session_log_entry() -> str:
    """Return the last non-empty paragraph from state/session_log.md, or '' if absent."""
    log_path = Path("state/session_log.md")
    if not log_path.exists():
        return ""
    text = log_path.read_text().strip()
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs[-1] if paragraphs else ""


def _run_beat_initialization(
    beat: dict,
    sr_ctx: str,
    narrator_ctx: str,
    last_log_entry: str,
    verbose: bool,
    log: logging.Logger,
) -> tuple[str, str]:
    """Run beat initialization for the first turn of a new beat.

    Writes character_plans, injects beat notes into contexts, calls the Narrator
    opener, handles verbose output, and logs the transition.
    Returns updated (sr_ctx, narrator_ctx).
    """
    character_plans = beat.get("character_plans", {})
    if character_plans:
        update_scene_state({"character_plans": character_plans})

    sr_ctx, narrator_ctx = _apply_beat_notes(beat, sr_ctx, narrator_ctx)
    run_beat_opener(beat, last_log_entry, verbose=verbose)

    if verbose:
        print(f"\n=== {beat['title']} ===")

    log.info(f"Beat transition: {beat['id']}")
    return sr_ctx, narrator_ctx


def _write_turn_file(
    logs_dir: Path,
    scene_num: int,
    beat_num: int,
    beat_id: str,
    turn_num: int,
    type: str,
    content: str,
) -> str:
    """Write turn intermediate file; return content for chaining."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"{scene_num:02d}_{beat_num:02d}_{beat_id}_{turn_num:04d}_{type}.txt"
    path.write_text(content)
    return content


def _extract_stat_changes(ruling_text: str) -> dict[str, int]:
    """Extract wounds and strain applied from a ruling text. Returns {wounds: N, strain: N}."""
    import re
    result: dict[str, int] = {}
    wounds_match = re.search(r"(\d+)\s+wound", ruling_text, re.IGNORECASE)
    strain_match = re.search(r"(\d+)\s+strain", ruling_text, re.IGNORECASE)
    if wounds_match:
        result["wounds"] = int(wounds_match.group(1))
    if strain_match:
        result["strain"] = int(strain_match.group(1))
    return result


def _build_actor_name_map(scene: dict, scene_yamls: dict) -> dict[str, str]:
    """Return {lowercase_display_name: char_id} from all character sources in the scene."""
    name_to_id: dict[str, str] = {}
    for char_id, yaml_data in scene_yamls.items():
        name = yaml_data.get("identity", {}).get("name", char_id)
        name_to_id[name.lower()] = char_id
    for npc in scene.get("inline_npcs", []):
        name_to_id[npc["name"].lower()] = npc["id"]
    for group in scene.get("minion_groups", []):
        name_to_id[group["name"].lower()] = group["id"]
    return name_to_id


def _make_ruling_callback(stats_path: Path, name_to_id: dict[str, str]):
    """Return an on_ruling callback that updates party_stats after each ruling."""
    def callback(actor: str, ruling_text: str) -> str:
        actor_key = name_to_id.get(actor.lower(), actor)
        changes = _extract_stat_changes(ruling_text)
        if changes:
            try:
                party_stats = load_party_stats(str(stats_path))
            except FileNotFoundError:
                party_stats = {"characters": {}}
            chars = party_stats.get("characters", {})
            char = chars.get(actor_key, {})
            if "wounds" in changes:
                char["wounds_current"] = char.get("wounds_current", 0) + changes["wounds"]
                threshold = char.get("wounds_threshold", 0)
                if threshold and char["wounds_current"] >= threshold:
                    session_log_path = Path("state/session_log.md")
                    with session_log_path.open("a") as f:
                        f.write(f"\n{actor} has reached wound threshold ({threshold})!\n")
            if "strain" in changes:
                char["strain_current"] = char.get("strain_current", 0) + changes["strain"]
            chars[actor_key] = char
            update_party_stats({"characters": chars}, str(stats_path))
        try:
            party_stats = load_party_stats(str(stats_path))
        except FileNotFoundError:
            party_stats = {"characters": {}}
        return "\n".join(
            f"{cid}: wounds {c.get('wounds_current', 0)}/{c.get('wounds_threshold', '?')}, "
            f"strain {c.get('strain_current', 0)}/{c.get('strain_threshold', '?')}"
            for cid, c in party_stats.get("characters", {}).items()
        )
    return callback


def _roll_specs(specs: list[dict]) -> None:
    """Add roll_result to each spec in-place using the embedded stat values."""
    for spec in specs:
        ability = max(spec["char_value"], spec["skill_rank"])
        proficiency = min(spec["char_value"], spec["skill_rank"])
        diff_word = spec["difficulty"].split()[0]
        diff_dice = _DIFFICULTY_MAP.get(diff_word, 2)
        result = roll_pool({"ability": ability, "proficiency": proficiency, "difficulty": diff_dice})
        outcome = "passed" if result.passed else "failed"
        spec["roll_result"] = (
            f"Roll {outcome}: net {result.net_successes:+d} successes, "
            f"{result.net_advantage:+d} advantage"
            + (f" | {result.triumphs} Triumph(s)" if result.triumphs else "")
            + (f" | {result.despairs} Despair(s)" if result.despairs else "")
        )


def run_turn_loop(scene: dict, verbose: bool = False, dump_prompts: bool = False) -> None:
    """Run the agent turn loop for a loaded adventure scene."""
    apply_litellm_settings()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = _setup_session_log(timestamp)
    prompts_path = setup_instrumentation(timestamp, dump_prompts=dump_prompts)
    logs_dir = Path("logs")

    agent_configs = load_agent_configs()
    print("Agents:")
    for name, cfg in agent_configs.items():
        print(f"  {name:<14} {cfg['model_alias']}")
    print(f"Prompt log:  {prompts_path}")

    initialize_scene_state(scene)
    initialize_npc_stats(scene)
    scene_yamls = load_scene_yamls(scene)
    actor_name_map = _build_actor_name_map(scene, scene_yamls)
    human_pc_name = _find_human_pc_name(scene)
    scene_num: int = scene.get("scene_num", 0)
    beat_list = scene.get("beats", [])
    beat_ids = [b["id"] for b in beat_list]

    print(f"\n=== {scene['title']} ===")
    print(scene["location"]["read_aloud"])
    log.info(f"Scene started: {scene['scene_id']}")

    _last_beat: str = ""
    _turn_num: int = 1
    _beat_num: int = 0

    while True:
        scene_state = load_scene_state()
        party_stats = load_party_stats()
        current_beat = scene_state.get("current_beat", "")
        last_actions = scene_state.get("last_actions", {})

        sr_ctx = render_show_runner_context(scene, scene_state, party_stats, last_actions)
        narrator_ctx = render_narrator_context(scene, current_beat, last_actions, party_stats)

        # ── Step 0: Beat initialization (first turn of each beat only) ───────
        if current_beat != _last_beat:
            beat = next((b for b in beat_list if b["id"] == current_beat), {})
            _beat_num = beat_ids.index(current_beat) if current_beat in beat_ids else 0
            last_log_entry = _read_last_session_log_entry()
            sr_ctx, narrator_ctx = _run_beat_initialization(beat, sr_ctx, narrator_ctx, last_log_entry, verbose, log)
            _last_beat = current_beat
            _turn_num = 1

        active_ids = _active_npc_ids(scene, current_beat)
        npc_chars = load_scene_characters(scene, scene_state, player_filter="npc", active_ids=active_ids)
        companion_chars = load_scene_characters(scene, scene_state, player_filter="companion")

        log.debug(f"Beat: {current_beat} turn: {_turn_num}  npcs: {list(npc_chars)}  companions: {list(companion_chars)}")
        print(f"\n--- Beat: {current_beat} (turn {_turn_num}) ---")

        # ── Step 1: Player input ─────────────────────────────────────────────
        player_action = prompt_player_action("Z-4P0")
        log.info(f"Player action: {player_action!r}")

        if player_action.strip().lower() in ("quit", "exit", "q"):
            print("Session ended.")
            log.info("Session ended by player.")
            break

        # ── Step 2: Companion wave ───────────────────────────────────────────
        actor_beat_ctx = render_actor_beat_context(scene, scene_state)
        companion_outputs, companion_summaries = run_companion_wave(companion_chars, actor_beat_ctx, player_action, pc_name=human_pc_name)
        log.info(f"Step 2 complete: {len(companion_outputs)} Companions voiced")

        # ── Step 3: NPC wave with inline summaries ───────────────────────────
        summaries_log_path = logs_dir / f"{scene_num:02d}_{_beat_num:02d}_{current_beat}_{_turn_num:04d}_summaries.txt"
        npc_outputs = run_npc_wave(npc_chars, actor_beat_ctx, player_action, companion_summaries, summaries_log_path, pc_name=human_pc_name)
        log.info(f"Step 3 complete: {len(npc_outputs)} NPCs voiced")

        # ── Step 4: Party action summaries ───────────────────────────────────
        party_actions = {"Z-4P0": player_action, **companion_outputs}
        run_summaries(party_actions, summaries_log_path)

        # ── Step 5: Check identification ─────────────────────────────────────
        char_summaries = _parse_summaries_log(summaries_log_path)
        all_summaries = summaries_log_path.read_text() if summaries_log_path.exists() else ""
        char_stats = _build_char_stats(
            scene_yamls,
            inline_npcs=[n for n in scene.get("inline_npcs", []) if n["id"] in active_ids],
            minion_groups=[g for g in scene.get("minion_groups", []) if g["id"] in active_ids],
        )
        check_output = run_checks(char_summaries, char_stats)
        checks_text = _write_turn_file(logs_dir, scene_num, _beat_num, current_beat, _turn_num, "checks", check_output)
        ruling_specs, _ = parse_structured(checks_text, _ruling_specs_parser, python_sample=_CHECK_PYTHON_SAMPLE)
        log.info(f"Step 5 complete: {len(ruling_specs)} checks identified")

        # ── Step 6: Dice rolling + rulings ──────────────────────────────────
        party_stats_path = Path("state/party_stats.yaml")
        _roll_specs(ruling_specs)
        rulings = run_rulings(
            ruling_specs,
            on_ruling=_make_ruling_callback(party_stats_path, actor_name_map) if ruling_specs else None,
        )
        results_text = "\n".join(f"{k}: {v}" for k, v in rulings.items()) if rulings else "No checks this turn."
        _write_turn_file(logs_dir, scene_num, _beat_num, current_beat, _turn_num, "results", results_text)
        log.info(f"Step 6 complete: {len(ruling_specs)} checks resolved")

        # ── Step 7: Resolution narrative (printed to player) ─────────────────
        pronoun_map: dict[str, str] = {}
        for char_id, yaml in scene_yamls.items():
            p = yaml.get("identity", {}).get("pronoun")
            if p:
                pronoun_map[char_id] = p
        for npc in scene.get("inline_npcs", []):
            if npc["id"] in active_ids and npc.get("pronoun"):
                pronoun_map[npc["id"]] = npc["pronoun"]
        for group in scene.get("minion_groups", []):
            if group["id"] in active_ids and group.get("pronoun"):
                pronoun_map[group["id"]] = group["pronoun"]
        narrative = run_narrative(all_summaries, checks_text, results_text, pronoun_map=pronoun_map or None)
        if narrative:
            label = "\n=== Resolution Narrative ===" if verbose else ""
            print(f"{label}\n{narrative}")

        # ── Step 8: Last-action extraction ───────────────────────────────────
        all_actors = {**npc_outputs, **party_actions}
        last_actions_extracted = run_last_actions(all_actors)
        if not last_actions_extracted:
            last_actions_extracted = all_actors

        # ── Step 9: Plan update ───────────────────────────────────────────────
        active_chars = {**npc_chars, **companion_chars}
        sr_plan_path = logs_dir / f"{scene_num:02d}_{_beat_num:02d}_{current_beat}_{_turn_num:04d}_sr_plan.txt"
        new_plans = run_plan_update(
            active_chars,
            all_summaries,
            results_text,
            last_actions_extracted,
            plan_log_path=sr_plan_path,
        )
        log.info("Turn complete")

        # ── State writes ──────────────────────────────────────────────────────
        update_scene_state({"last_actions": last_actions_extracted})
        if new_plans:
            update_scene_state({"character_plans": new_plans})

        if narrative:
            session_log_path = Path("state/session_log.md")
            with session_log_path.open("a") as f:
                f.write(f"{narrative}\n\n")
            log.info(f"Session log: {narrative[:120]}")

        # ── Beat advancement ──────────────────────────────────────────────────
        choice = _beat_prompt(scene, current_beat)
        if choice in ("quit", "exit", "q"):
            print("Session ended.")
            log.info("Session ended by player.")
            break

        if choice == "stay":
            log.info(f"Staying on beat: {current_beat}")
        elif choice == "advance":
            next_id = _next_beat_id(scene, current_beat)
            if next_id:
                advance_beat(next_id)
                log.info(f"Advanced to beat: {next_id}")
            else:
                print("Scene complete.")
                log.info("Scene complete — no more beats.")
                break
        else:
            advance_beat(choice)
            log.info(f"Jumped to beat: {choice}")

        _turn_num += 1
