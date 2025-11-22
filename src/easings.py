import math


def apply_easing(easing_id: int, t: float) -> float:
    """
    Apply the specified easing function to the input t (0 <= t <= 1).
    :param easing_id: The ID of the easing function.
    :param t: The input value to be eased, typically between 0 and 1.
    :return: The eased value.
    """

    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0

    easing_map = {
        0: lambda t: t,  # Linear
        1: quad_out,  # easing out, something legacy..
        2: quad_in,  # easing in, something legacy..
        # quad
        3: quad_in,
        4: quad_out,
        5: quad_in_out,
        # cubic
        6: cubic_in,
        7: cubic_out,
        8: cubic_in_out,
        # quart
        9: quart_in,
        10: quart_out,
        11: quart_in_out,
        # quint
        12: quint_in,
        13: quint_out,
        14: quint_in_out,
        # sine
        15: sine_in,
        16: sine_out,
        17: sine_in_out,
        # expo
        18: expo_in,
        19: expo_out,
        20: expo_in_out,
        # circ
        21: circ_in,
        22: circ_out,
        23: circ_in_out,
        # elastic
        24: elastic_in,
        25: elastic_out,
        26: elastic_out_half,
        27: elastic_out_quarter,
        28: elastic_in_out,
        # back
        29: back_in,
        30: back_out,
        31: back_in_out,
        # bounce
        32: bounce_in,
        33: bounce_out,
        34: bounce_in_out,
    }

    func = easing_map.get(easing_id, lambda t: t)  # Default to linear if not found
    return func(t)


def _reverse(function: callable, value: float) -> float:
    return 1 - function(1 - value)


def _to_in_out(function: callable, value: float) -> float:
    return 0.5 * (function(2 * value) if value < 0.5 else (2 - function(2 - 2 * value)))


def quad_in(t: float) -> float:
    return t * t


def quad_out(t: float) -> float:
    return _reverse(quad_in, t)


def quad_in_out(t: float) -> float:
    return _to_in_out(quad_in, t)


def cubic_in(t: float) -> float:
    return t * t * t


def cubic_out(t: float) -> float:
    return _reverse(cubic_in, t)


def cubic_in_out(t: float) -> float:
    return _to_in_out(cubic_in, t)


def quart_in(t: float) -> float:
    return t * t * t * t


def quart_out(t: float) -> float:
    return _reverse(quart_in, t)


def quart_in_out(t: float) -> float:
    return _to_in_out(quart_in, t)


def quint_in(t: float) -> float:
    return t * t * t * t * t


def quint_out(t: float) -> float:
    return _reverse(quint_in, t)


def quint_in_out(t: float) -> float:
    return _to_in_out(quint_in, t)


def sine_in(t: float) -> float:
    return 1 - math.cos((t * math.pi) / 2)


def sine_out(t: float) -> float:
    return _reverse(sine_in, t)


def sine_in_out(t: float) -> float:
    return _to_in_out(sine_in, t)


def expo_in(t: float) -> float:
    return math.pow(2, 10 * (t - 1))


def expo_out(t: float) -> float:
    return _reverse(expo_in, t)


def expo_in_out(t: float) -> float:
    return _to_in_out(expo_in, t)


def circ_in(t: float) -> float:
    return 1 - math.sqrt(1 - t * t)


def circ_out(t: float) -> float:
    return _reverse(circ_in, t)


def circ_in_out(t: float) -> float:
    return _to_in_out(circ_in, t)


def back_in(t: float) -> float:
    s = 1.70158
    return t * t * ((s + 1) * t - s)


def back_out(t: float) -> float:
    return _reverse(back_in, t)


def back_in_out(t: float) -> float:
    return _to_in_out(back_in, t)


def bounce_out(t: float) -> float:
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


def bounce_in(t: float) -> float:
    return _reverse(bounce_out, t)


def bounce_in_out(t: float) -> float:
    return _to_in_out(bounce_in, t)


def elastic_in(t: float) -> float:
    return _reverse(elastic_out, t)


def elastic_out(t: float) -> float:
    return math.pow(2, -10 * t) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1


def elastic_out_half(t: float) -> float:
    return math.pow(2, -10 * t) * math.sin((0.5 * t - 0.075) * (2 * math.pi) / 0.3) + 1


def elastic_out_quarter(t: float) -> float:
    return math.pow(2, -10 * t) * math.sin((0.25 * t - 0.075) * (2 * math.pi) / 0.3) + 1


def elastic_in_out(t: float) -> float:
    return _to_in_out(elastic_in, t)
