STARTUP_DELAY = 5
ATTACH_STARTUP_DELAY = 1
GAME_ATTACH_WAIT_SECONDS = 2.0


def should_launch_new_game_process(existing_rect):
    return existing_rect is None
