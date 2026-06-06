"""Unit tests for src/state_engine.py — StateEngine interpolation and state computation."""

import pytest
from src.models import (
    Storyboard, Sprite, Animation, VideoObject,
    Layer, Origin, LoopType, Command, LoopCommand, Vector2, ObjectState,
)
from src.state_engine import StateEngine


# ---------------------------------------------------------------------------
# Life time calculation
# ---------------------------------------------------------------------------
class TestLifetime:
    def test_no_commands_zero_lifetime(self):
        """Object with no commands gets life_start=0, life_end=0."""
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        sb.add_object(obj)
        engine = StateEngine(sb)
        assert obj.life_start == 0
        assert obj.life_end == 0

    def test_single_command_lifetime(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 1000, 2000, [0.0, 1.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        assert obj.life_start == 1000
        assert obj.life_end == 2000

    def test_multiple_commands_lifetime(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 500, 1500, [0.0, 1.0]))
        obj.commands.append(Command("M", 0, 2000, 3000, [0, 0, 320, 240]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        assert obj.life_start == 500
        assert obj.life_end == 3000

    def test_loop_extends_lifetime(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        loop = LoopCommand(3000, 2)
        loop.commands.append(Command("F", 0, 0, 500, [0.0, 1.0]))
        obj.commands.append(loop)
        sb.add_object(obj)
        engine = StateEngine(sb)
        # Loop: start=3000, sub_max=500, loop_count=2
        # end = 3000 + 500*2 = 4000
        assert obj.life_start == 3000
        assert obj.life_end == 4000

    def test_lifetime_commands_sorted(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        # Add commands out of order
        obj.commands.append(Command("F", 0, 3000, 4000, [0.0, 1.0]))
        obj.commands.append(Command("M", 0, 1000, 2000, [0, 0, 320, 240]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        assert obj.life_start == 1000
        assert obj.life_end == 4000


# ---------------------------------------------------------------------------
# Basic interpolation
# ---------------------------------------------------------------------------
class TestBasicInterpolation:
    def test_before_lifetime_returns_none(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 1000, 2000, [0.0, 1.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        assert engine.get_object_state(obj, 500) is None

    def test_after_lifetime_returns_none(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 1000, 2000, [0.0, 1.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        assert engine.get_object_state(obj, 2500) is None

    def test_visible_when_in_range(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 1000, 2000, [0.0, 1.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state is not None
        assert state.visible is True


# ---------------------------------------------------------------------------
# Fade (F) interpolation
# ---------------------------------------------------------------------------
class TestFadeInterpolation:
    def test_fade_start(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 1000, 2000, [0.0, 1.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        # At exact start time, opacity=0.0 < 0.001 → object is None (invisible)
        state = engine.get_object_state(obj, 1000)
        assert state is None

    def test_fade_end(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 1000, 2000, [0.0, 1.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.opacity == pytest.approx(1.0)

    def test_fade_midpoint_linear(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 1000, 2000, [0.0, 1.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state.opacity == pytest.approx(0.5)

    def test_fade_with_easing(self):
        """Quad-out easing at t=0.5 should yield >0.5."""
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 4, 1000, 2000, [0.0, 1.0]))  # quad_out
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state.opacity > 0.5

    def test_near_zero_opacity_returns_none(self):
        """Opacity < 0.001 should make the object invisible (None)."""
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 1000, [0.0, 0.0001]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        # At start (0ms), opacity = 0 → None
        state = engine.get_object_state(obj, 0)
        assert state is None


# ---------------------------------------------------------------------------
# Move (M, MX, MY) interpolation
# ---------------------------------------------------------------------------
class TestMoveInterpolation:
    def test_move_start(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))  # keep visible
        obj.commands.append(Command("M", 0, 1000, 2000, [0, 0, 320, 240]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1000)
        assert state.position == Vector2(0, 0)

    def test_move_end(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("M", 0, 1000, 2000, [0, 0, 320, 240]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.position == Vector2(320, 240)

    def test_move_midpoint(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("M", 0, 1000, 2000, [0, 0, 320, 240]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state.position == Vector2(160, 120)

    def test_move_x_only(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("MX", 0, 1000, 2000, [0, 320]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.position.x == 320
        assert state.position.y == 0  # unchanged

    def test_move_y_only(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("MY", 0, 1000, 2000, [0, 240]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.position.y == 240
        assert state.position.x == 0  # unchanged


# ---------------------------------------------------------------------------
# Scale (S, V) interpolation
# ---------------------------------------------------------------------------
class TestScaleInterpolation:
    def test_scale_uniform(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("S", 0, 1000, 2000, [1.0, 2.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.scale_vec == Vector2(2.0, 2.0)

    def test_scale_vec(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("V", 0, 1000, 2000, [1.0, 1.0, 2.0, 0.5]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.scale_vec == Vector2(2.0, 0.5)


# ---------------------------------------------------------------------------
# Rotation (R) interpolation
# ---------------------------------------------------------------------------
class TestRotationInterpolation:
    def test_rotation_linear(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("R", 0, 1000, 2000, [0.0, 3.14159]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.rotation == pytest.approx(3.14159)
        mid = engine.get_object_state(obj, 1500)
        assert mid.rotation == pytest.approx(1.570795)


# ---------------------------------------------------------------------------
# Color (C) interpolation
# ---------------------------------------------------------------------------
class TestColorInterpolation:
    def test_color_change(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("C", 0, 1000, 2000, [255, 255, 255, 128, 64, 32]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2000)
        assert state.r == 128
        assert state.g == 64
        assert state.b == 32

    def test_color_midpoint(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("C", 0, 1000, 2000, [0, 0, 0, 100, 100, 100]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state.r == pytest.approx(50)
        assert state.g == pytest.approx(50)
        assert state.b == pytest.approx(50)


# ---------------------------------------------------------------------------
# Parameter commands (P)
# ---------------------------------------------------------------------------
class TestParameterCommands:
    def test_flip_horizontal(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("P", 0, 1000, 2000, ["H"]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state.flip_h is True

    def test_flip_vertical(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("P", 0, 1000, 2000, ["V"]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state.flip_v is True

    def test_additive_blending(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("P", 0, 1000, 2000, ["A"]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1500)
        assert state.additive is True

    def test_parameter_not_applied_after_end(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("P", 0, 1000, 2000, ["H"]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2500)
        # After end time, parameter should NOT be applied
        assert state.flip_h is False

    def test_parameter_applied_even_before_start(self):
        """NOTE: current implementation applies P commands whenever time <= end_time,
        even if time < start_time. This may be unintentional but is the actual behaviour."""
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 3000, [1.0, 1.0]))
        obj.commands.append(Command("P", 0, 1500, 2500, ["A"]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 1000)
        # P is active from t=0 to t=end_time (no start_time gate)
        assert state.additive is True


# ---------------------------------------------------------------------------
# Loop command processing
# ---------------------------------------------------------------------------
class TestLoopProcessing:
    def test_loop_iteration_before_start(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 500, 4500, [1.0, 1.0]))  # visible
        loop = LoopCommand(1000, 3)
        loop.commands.append(Command("F", 0, 0, 500, [0.0, 1.0]))
        loop.commands.append(Command("F", 0, 500, 1000, [1.0, 0.0]))
        obj.commands.append(loop)
        sb.add_object(obj)
        engine = StateEngine(sb)
        # Before loop: obj is visible from top-level F(500, 4500)
        state = engine.get_object_state(obj, 800)
        assert state is not None
        assert state.visible is True

    def test_loop_first_iteration(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        loop = LoopCommand(1000, 2)
        loop.commands.append(Command("F", 0, 0, 500, [0.0, 1.0]))
        loop.commands.append(Command("F", 0, 500, 1000, [1.0, 0.0]))
        obj.commands.append(loop)
        sb.add_object(obj)
        engine = StateEngine(sb)
        # t=1250 → loop iteration 0, time_in=250 → opacity should be 0.5
        state = engine.get_object_state(obj, 1250)
        assert state is not None
        assert state.opacity == pytest.approx(0.5)

    def test_loop_second_iteration(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        loop = LoopCommand(1000, 2)
        loop.commands.append(Command("F", 0, 0, 500, [0.0, 1.0]))
        loop.commands.append(Command("F", 0, 500, 1000, [1.0, 0.0]))
        obj.commands.append(loop)
        sb.add_object(obj)
        engine = StateEngine(sb)
        # t=2250 → loop iteration 1, time_in=250 → same as iteration 0
        state = engine.get_object_state(obj, 2250)
        assert state is not None
        assert state.opacity == pytest.approx(0.5)

    def test_loop_after_end(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        loop = LoopCommand(1000, 2)
        loop.commands.append(Command("F", 0, 0, 500, [0.0, 1.0]))
        loop.commands.append(Command("F", 0, 500, 1000, [1.0, 0.0]))
        obj.commands.append(loop)
        sb.add_object(obj)
        engine = StateEngine(sb)
        # After loop (1000 + 2*1000 = 3000): holds end state
        state = engine.get_object_state(obj, 3500)
        assert state is None  # no top-level fade → loop ended → after life


# ---------------------------------------------------------------------------
# Category deduplication
# ---------------------------------------------------------------------------
class TestCategoryDeduplication:
    def test_mx_overrides_m_x(self):
        """MX should prevent M from overriding x after MX is processed."""
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 5000, [1.0, 1.0]))
        # M sets x,y at 1000-2000
        obj.commands.append(Command("M", 0, 1000, 2000, [0, 0, 100, 100]))
        # MX overrides x at 1500-2500
        obj.commands.append(Command("MX", 0, 1500, 2500, [100, 300]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2500)
        # MX should set x=300. M also covers y (since MY never appeared)
        assert state.position.x == pytest.approx(300)
        assert state.position.y == pytest.approx(100)  # from M's end state

    def test_my_overrides_m_y(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 5000, [1.0, 1.0]))
        obj.commands.append(Command("M", 0, 1000, 2000, [0, 0, 100, 200]))
        obj.commands.append(Command("MY", 0, 1500, 2500, [200, 50]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2500)
        assert state.position.y == pytest.approx(50)
        assert state.position.x == pytest.approx(100)  # from M

    def test_v_overrides_s_scale(self):
        """V and S both affect 'scale' category. Later V should override."""
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 5000, [1.0, 1.0]))
        obj.commands.append(Command("S", 0, 1000, 2000, [1.0, 2.0]))
        obj.commands.append(Command("V", 0, 1500, 2500, [2.0, 2.0, 3.0, 4.0]))
        sb.add_object(obj)
        engine = StateEngine(sb)
        state = engine.get_object_state(obj, 2500)
        assert state.scale_vec == Vector2(3.0, 4.0)


# ---------------------------------------------------------------------------
# Animation frame calculation
# ---------------------------------------------------------------------------
class TestAnimationFrames:
    def test_animation_frame_zero(self):
        sb = Storyboard()
        anim = Animation(
            Layer.Pass, Origin.Centre, "frames/f.png", Vector2(0, 0),
            frame_count=8, frame_delay=50.0, loop_type=LoopType.LoopForever,
        )
        anim.commands.append(Command("F", 0, 0, 5000, [1.0, 1.0]))
        sb.add_object(anim)
        engine = StateEngine(sb)
        state = engine.get_object_state(anim, 0)
        assert state.frame_index == 0
        assert state.image_path == "frames/f0.png"

    def test_animation_frame_mid(self):
        sb = Storyboard()
        anim = Animation(
            Layer.Pass, Origin.Centre, "frames/f.png", Vector2(0, 0),
            frame_count=8, frame_delay=50.0, loop_type=LoopType.LoopForever,
        )
        anim.commands.append(Command("F", 0, 0, 5000, [1.0, 1.0]))
        sb.add_object(anim)
        engine = StateEngine(sb)
        state = engine.get_object_state(anim, 125)
        # run_time = 125, frame = 125 // 50 = 2
        assert state.frame_index == 2
        assert state.image_path == "frames/f2.png"

    def test_animation_loop_forever_wraps(self):
        sb = Storyboard()
        anim = Animation(
            Layer.Pass, Origin.Centre, "frames/f.png", Vector2(0, 0),
            frame_count=4, frame_delay=50.0, loop_type=LoopType.LoopForever,
        )
        anim.commands.append(Command("F", 0, 0, 10000, [1.0, 1.0]))
        sb.add_object(anim)
        engine = StateEngine(sb)
        # total_frame_time = 200ms. t=300 → current_loop_time=300%200=100 → frame=2
        state = engine.get_object_state(anim, 300)
        assert state.frame_index == 2

    def test_animation_loop_once_stops(self):
        sb = Storyboard()
        anim = Animation(
            Layer.Pass, Origin.Centre, "frames/f.png", Vector2(0, 0),
            frame_count=4, frame_delay=50.0, loop_type=LoopType.LoopOnce,
        )
        anim.commands.append(Command("F", 0, 0, 10000, [1.0, 1.0]))
        sb.add_object(anim)
        engine = StateEngine(sb)
        # total=200ms, t=500 → holds frame_index=3
        state = engine.get_object_state(anim, 500)
        assert state.frame_index == 3  # last frame

    def test_animation_zero_frames(self):
        sb = Storyboard()
        anim = Animation(
            Layer.Pass, Origin.Centre, "frames/f.png", Vector2(0, 0),
            frame_count=0, frame_delay=50.0,
        )
        anim.commands.append(Command("F", 0, 0, 5000, [1.0, 1.0]))
        sb.add_object(anim)
        engine = StateEngine(sb)
        state = engine.get_object_state(anim, 100)
        assert state.frame_index == 0  # no update


# ---------------------------------------------------------------------------
# Zero-duration P commands inside loops
# ---------------------------------------------------------------------------
class TestPLoopExpansion:
    def test_p_command_expanded_to_loop_duration(self):
        sb = Storyboard()
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        obj.commands.append(Command("F", 0, 0, 5000, [1.0, 1.0]))
        loop = LoopCommand(1000, 2)
        loop.commands.append(Command("P", 0, 0, 0, ["H"]))
        loop.commands.append(Command("S", 0, 0, 500, [1.0, 2.0]))
        obj.commands.append(loop)
        sb.add_object(obj)
        engine = StateEngine(sb)
        # The P command's end_time should be expanded to sub_max (500)
        state = engine.get_object_state(obj, 1200)
        assert state.flip_h is True


# ---------------------------------------------------------------------------
# StateEngine construction
# ---------------------------------------------------------------------------
class TestConstruction:
    def test_empty_storyboard(self):
        sb = Storyboard()
        engine = StateEngine(sb)
        assert engine.storyboard is sb

    def test_storyboard_with_mixed_objects(self):
        sb = Storyboard()
        sb.add_object(Sprite(Layer.Background, Origin.Centre, "bg.png", Vector2(0, 0)))
        sb.add_object(Sprite(Layer.Pass, Origin.Centre, "pass.png", Vector2(0, 0)))
        sb.video = VideoObject("v.mp4", 0)
        engine = StateEngine(sb)
        assert len(engine.storyboard.background_layer) == 1
        assert len(engine.storyboard.pass_layer) == 1


# ---------------------------------------------------------------------------
# Integration: parser + state engine
# ---------------------------------------------------------------------------
class TestParserStateEngineIntegration:
    def test_parsed_object_has_state(self):
        import os, tempfile
        from src.parser import StoryboardParser

        content = """
[Events]
Sprite,Pass,Centre,"test.png",320,240
_F,0,1000,2000,0,1
_M,0,2000,3000,320,240,400,300
"""
        fd, path = tempfile.mkstemp(suffix=".osb", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            engine = StateEngine(sb)
            obj = sb.pass_layer[0]

            state = engine.get_object_state(obj, 1500)
            assert state.opacity == pytest.approx(0.5)

            state = engine.get_object_state(obj, 2500)
            assert state.position.x == pytest.approx(360)
            assert state.position.y == pytest.approx(270)
        finally:
            os.unlink(path)
