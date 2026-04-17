FINGER_ANCHOR_NORM = (0.0071, 0.1389)


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def sprite_top_left_for_target(
    *,
    target_x,
    target_y,
    sprite_width,
    sprite_height,
    scale,
    anchor_norm_x=FINGER_ANCHOR_NORM[0],
    anchor_norm_y=FINGER_ANCHOR_NORM[1],
):
    return (
        target_x - (sprite_width * scale * anchor_norm_x),
        target_y - (sprite_height * scale * anchor_norm_y),
    )
