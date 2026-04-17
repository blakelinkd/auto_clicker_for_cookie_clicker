CLICK_STACK_BUFF_KEYS = {
    "Click frenzy",
    "Dragonflight",
}

PRODUCTION_STACK_BUFF_KEYS = {
    "Frenzy",
    "Dragon Harvest",
    "Elder frenzy",
    "Building special",
}

MAJOR_PRODUCTION_BUFF_KEYS = {
    "Dragon Harvest",
    "Elder frenzy",
    "Building special",
}

VALUABLE_BUFF_KEYS = CLICK_STACK_BUFF_KEYS | PRODUCTION_STACK_BUFF_KEYS


def evaluate_combo_buffs(buff_names, *, spell_ready=False):
    names = {name for name in (buff_names or set()) if name}
    click_buffs = names & CLICK_STACK_BUFF_KEYS
    production_buffs = names & PRODUCTION_STACK_BUFF_KEYS
    major_production_buffs = names & MAJOR_PRODUCTION_BUFF_KEYS

    can_spawn_click_buff = bool(production_buffs) and (
        len(production_buffs) >= 2 or bool(major_production_buffs)
    )
    should_fire_godzamok = bool(click_buffs) and bool(production_buffs)

    if should_fire_godzamok:
        stage = "execute_click_combo"
    elif can_spawn_click_buff:
        stage = "spawn_click_buff"
    elif production_buffs:
        stage = "build_combo"
    else:
        stage = "idle"

    if should_fire_godzamok:
        phase = "execute"
    elif production_buffs and (bool(spell_ready) or can_spawn_click_buff):
        phase = "fish"
    elif production_buffs:
        phase = "setup"
    else:
        phase = "idle"

    return {
        "buff_names": names,
        "click_buffs": click_buffs,
        "production_buffs": production_buffs,
        "major_production_buffs": major_production_buffs,
        "can_spawn_click_buff": can_spawn_click_buff,
        "should_fire_godzamok": should_fire_godzamok,
        "stage": stage,
        "phase": phase,
    }
