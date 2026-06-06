"""Unit tests for src/easings.py — all 34 osu! easing functions."""

import math
import pytest
from src.easings import (
    apply_easing,
    quad_in, quad_out, quad_in_out,
    cubic_in, cubic_out, cubic_in_out,
    quart_in, quart_out, quart_in_out,
    quint_in, quint_out, quint_in_out,
    sine_in, sine_out, sine_in_out,
    expo_in, expo_out, expo_in_out,
    circ_in, circ_out, circ_in_out,
    elastic_in, elastic_out, elastic_out_half, elastic_out_quarter, elastic_in_out,
    back_in, back_out, back_in_out,
    bounce_in, bounce_out, bounce_in_out,
)


# ---------------------------------------------------------------------------
# Boundary behaviour shared by all easing functions
# ---------------------------------------------------------------------------
ALL_EASING_IDS = list(range(35))  # 0–34


def test_apply_easing_t_zero():
    """Any easing at t=0 should return approximately 0."""
    # expo_in(0) = 2^-10 ≈ 0.001, so use a tolerance that covers all easings
    for eid in ALL_EASING_IDS:
        result = apply_easing(eid, 0.0)
        assert abs(result) < 0.002, f"Easing {eid}: expected ~0 at t=0, got {result}"


def test_apply_easing_t_one():
    """Any easing at t=1 should return approximately 1."""
    # expo_out(1) = 1 - 2^-10 ≈ 0.999, elastic functions can overshoot slightly
    for eid in ALL_EASING_IDS:
        result = apply_easing(eid, 1.0)
        assert abs(result - 1.0) < 0.002, f"Easing {eid}: expected ~1 at t=1, got {result}"


def test_apply_easing_clamps_negative():
    """t < 0 should be clamped to 0."""
    for eid in [0, 1, 3, 6, 9, 12, 15, 18, 21, 24, 29, 32]:
        val = apply_easing(eid, -0.5)
        # The result should equal the easing at t=0 (which is 0)
        expected = apply_easing(eid, 0.0)
        assert val == expected, f"Easing {eid}: t=-0.5 not clamped"


def test_apply_easing_clamps_above_one():
    """t > 1 should be clamped to 1."""
    for eid in [0, 1, 3, 6, 9, 12, 15, 18, 21, 24, 29, 32]:
        val = apply_easing(eid, 1.5)
        expected = apply_easing(eid, 1.0)
        assert val == expected, f"Easing {eid}: t=1.5 not clamped"


def test_apply_easing_unknown_id_defaults_to_linear():
    """Unknown easing IDs should fall back to linear (identity)."""
    assert apply_easing(999, 0.3) == pytest.approx(0.3)
    assert apply_easing(-1, 0.7) == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# Linear (id=0)
# ---------------------------------------------------------------------------
class TestLinear:
    def test_identity(self):
        assert apply_easing(0, 0.0) == 0.0
        assert apply_easing(0, 0.25) == 0.25
        assert apply_easing(0, 0.5) == 0.5
        assert apply_easing(0, 0.75) == 0.75
        assert apply_easing(0, 1.0) == 1.0


# ---------------------------------------------------------------------------
# Quad (ids 1-5)
# ---------------------------------------------------------------------------
class TestQuad:
    def test_quad_in_midpoint(self):
        assert quad_in(0.5) == pytest.approx(0.25)

    def test_quad_out_midpoint(self):
        assert quad_out(0.5) == pytest.approx(0.75)

    def test_quad_in_out_symmetry(self):
        assert quad_in_out(0.25) == pytest.approx(1 - quad_in_out(0.75), rel=1e-6)

    def test_easing_id_1_is_legacy_out(self):
        """Legacy easing-out (id=1) should return >0.5 at t=0.5"""
        assert apply_easing(1, 0.5) > 0.5

    def test_easing_id_2_is_legacy_in(self):
        """Legacy easing-in (id=2) should return <0.5 at t=0.5"""
        assert apply_easing(2, 0.5) < 0.5

    def test_all_quad_ids(self):
        for eid in [3, 4, 5]:
            assert 0 <= apply_easing(eid, 0.5) <= 1


# ---------------------------------------------------------------------------
# Cubic (ids 6-8)
# ---------------------------------------------------------------------------
class TestCubic:
    def test_cubic_in(self):
        assert cubic_in(0.5) == pytest.approx(0.125)

    def test_cubic_out(self):
        assert cubic_out(0.5) == pytest.approx(0.875)

    def test_cubic_in_out_symmetry(self):
        assert cubic_in_out(0.4) == pytest.approx(1 - cubic_in_out(0.6), rel=1e-6)


# ---------------------------------------------------------------------------
# Quart (ids 9-11)
# ---------------------------------------------------------------------------
class TestQuart:
    def test_quart_in_half(self):
        assert quart_in(0.5) == pytest.approx(0.0625)

    def test_quart_out_half(self):
        assert quart_out(0.5) == pytest.approx(0.9375)


# ---------------------------------------------------------------------------
# Quint (ids 12-14)
# ---------------------------------------------------------------------------
class TestQuint:
    def test_quint_in_half(self):
        assert quint_in(0.5) == pytest.approx(0.03125)

    def test_quint_out_half(self):
        assert quint_out(0.5) == pytest.approx(0.96875)


# ---------------------------------------------------------------------------
# Sine (ids 15-17)
# ---------------------------------------------------------------------------
class TestSine:
    def test_sine_in_extrema(self):
        assert sine_in(0.0) == 0.0
        assert sine_in(1.0) == pytest.approx(1.0)

    def test_sine_in_half(self):
        val = sine_in(0.5)
        assert 0 < val < 1

    def test_sine_out_half(self):
        val = sine_out(0.5)
        assert 0 < val < 1


# ---------------------------------------------------------------------------
# Expo (ids 18-20)
# ---------------------------------------------------------------------------
class TestExpo:
    def test_expo_in_half(self):
        # expo_in(0.5) = 2^(10 * -0.5) = 2^-5 = 1/32 ≈ 0.03125
        assert expo_in(0.5) == pytest.approx(1 / 32, abs=1e-6)

    def test_expo_out_half(self):
        # expo_out(0.5) = 1 - expo_in(0.5) ≈ 0.96875
        assert expo_out(0.5) == pytest.approx(1 - 1 / 32, abs=1e-6)


# ---------------------------------------------------------------------------
# Circ (ids 21-23)
# ---------------------------------------------------------------------------
class TestCirc:
    def test_circ_in_extrema(self):
        assert circ_in(0.0) == 0.0
        assert circ_in(1.0) == 1.0

    def test_circ_out_extrema(self):
        assert circ_out(0.0) == 0.0
        assert circ_out(1.0) == 1.0

    def test_circ_in_out_range(self):
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            val = circ_in_out(t)
            assert 0.0 <= val <= 1.0, f"circ_in_out({t}) = {val}"


# ---------------------------------------------------------------------------
# Elastic (ids 24-28)
# ---------------------------------------------------------------------------
class TestElastic:
    def test_elastic_out_extrema(self):
        # elastic_out uses sin() internally — floating-point noise is expected
        assert elastic_out(0.0) == pytest.approx(0.0, abs=1e-6)
        assert elastic_out(1.0) == pytest.approx(1.0, abs=1e-3)

    def test_elastic_in_extrema(self):
        assert elastic_in(0.0) == pytest.approx(0.0, abs=1e-3)
        assert elastic_in(1.0) == pytest.approx(1.0, abs=1e-3)

    def test_elastic_overshoot(self):
        """Elastic functions can overshoot 0–1 due to oscillation."""
        # At certain points elastic_out can go slightly above 1
        val_out = elastic_out(0.2)
        # Just verify it doesn't throw and produces a number
        assert isinstance(val_out, float)
        assert not math.isnan(val_out)

    def test_elastic_out_half(self):
        val = elastic_out_half(0.5)
        assert isinstance(val, float)
        assert not math.isnan(val)

    def test_elastic_out_quarter(self):
        val = elastic_out_quarter(0.5)
        assert isinstance(val, float)
        assert not math.isnan(val)


# ---------------------------------------------------------------------------
# Back (ids 29-31)
# ---------------------------------------------------------------------------
class TestBack:
    def test_back_in_backtrack(self):
        """back_in overshoots negative before rising — should dip below 0"""
        val = back_in(0.2)
        # back_in goes negative for small t
        assert val < 0, f"Expected back_in(0.2) < 0, got {val}"

    def test_back_out_overshoot(self):
        """back_out overshoots above 1 before settling"""
        val = back_out(0.8)
        assert val > 1, f"Expected back_out(0.8) > 1, got {val}"

    def test_back_in_extrema(self):
        assert back_in(0.0) == 0.0
        assert back_in(1.0) == pytest.approx(1.0)

    def test_back_out_extrema(self):
        assert back_out(0.0) == pytest.approx(0.0, abs=1e-12)
        assert back_out(1.0) == 1.0


# ---------------------------------------------------------------------------
# Bounce (ids 32-34)
# ---------------------------------------------------------------------------
class TestBounce:
    def test_bounce_out_extrema(self):
        assert bounce_out(0.0) == 0.0
        assert bounce_out(1.0) == 1.0

    def test_bounce_out_rises_only(self):
        """bounce_out is monotonically increasing? Actually it bounces... but stays in range"""
        for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
            val = bounce_out(t)
            assert 0.0 <= val <= 1.0, f"bounce_out({t}) = {val} out of [0,1]"

    def test_bounce_in_extrema(self):
        assert bounce_in(0.0) == 0.0
        assert bounce_in(1.0) == 1.0

    def test_bounce_in_out_extrema(self):
        assert bounce_in_out(0.0) == 0.0
        assert bounce_in_out(1.0) == 1.0

    def test_bounce_out_known_point(self):
        """At t=1/2.75/2 the first bounce segment ends."""
        t = 1 / (2 * 2.75)
        val = bounce_out(t)
        expected = 7.5625 * t * t
        assert val == pytest.approx(expected, abs=1e-8)


# ---------------------------------------------------------------------------
# Easing ID mapping (verify the dispatch table covers all IDs)
# ---------------------------------------------------------------------------
class TestEasingDispatch:
    def test_all_ids_produce_value(self):
        """Every ID 0-34 should produce a float without error."""
        for eid in range(35):
            for t in [0.0, 0.3, 0.7, 1.0]:
                result = apply_easing(eid, t)
                assert isinstance(result, float), f"easing {eid} at t={t}"

    def test_easing_id_0_is_linear(self):
        assert apply_easing(0, 0.3) == 0.3

    def test_easing_in_less_than_out_at_midpoint(self):
        """Ease-in functions should be below ease-out at t=0.5."""
        # quad_in(0.5)=0.25, quad_out(0.5)=0.75
        assert quad_in(0.5) < quad_out(0.5)
        assert cubic_in(0.5) < cubic_out(0.5)
        assert quart_in(0.5) < quart_out(0.5)
        assert quint_in(0.5) < quint_out(0.5)

    def test_in_out_midpoint_is_half(self):
        """All in-out functions should hit 0.5 at t=0.5."""
        for func in [
            quad_in_out, cubic_in_out, quart_in_out, quint_in_out,
            sine_in_out, expo_in_out, circ_in_out,
        ]:
            val = func(0.5)
            assert val == pytest.approx(0.5, abs=1e-9), f"{func.__name__}(0.5) = {val}"
