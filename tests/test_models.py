"""Unit tests for src/models.py — dataclass models and enums."""

import pytest
from src.models import (
    Layer,
    Origin,
    LoopType,
    Command,
    LoopCommand,
    Vector2,
    SBObject,
    Sprite,
    Animation,
    ObjectState,
    VideoObject,
    Storyboard,
)


# ---------------------------------------------------------------------------
# Vector2
# ---------------------------------------------------------------------------
class TestVector2:
    def test_default_construction(self):
        v = Vector2(0.0, 0.0)
        assert v.x == 0.0
        assert v.y == 0.0

    def test_equality(self):
        assert Vector2(1.0, 2.0) == Vector2(1.0, 2.0)
        assert Vector2(1.0, 2.0) != Vector2(1.0, 3.0)
        assert Vector2(1.0, 2.0) != (1.0, 2.0)  # not a Vector2
        assert Vector2(0.0, 0.0) != None

    def test_add(self):
        a = Vector2(1.0, 2.0)
        b = Vector2(3.0, 4.0)
        r = a + b
        assert r == Vector2(4.0, 6.0)
        # original operands unchanged
        assert a == Vector2(1.0, 2.0)

    def test_sub(self):
        a = Vector2(5.0, 7.0)
        b = Vector2(2.0, 3.0)
        assert a - b == Vector2(3.0, 4.0)

    def test_mul_scalar(self):
        v = Vector2(2.0, 3.0)
        assert v * 2.0 == Vector2(4.0, 6.0)
        assert v * 0.5 == Vector2(1.0, 1.5)
        assert v * -1.0 == Vector2(-2.0, -3.0)

    def test_negative_values(self):
        v = Vector2(-1.5, -2.5)
        assert v.x == -1.5
        assert v.y == -2.5


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TestEnums:
    def test_layer_values(self):
        assert Layer.Background.value == 0
        assert Layer.Fail.value == 1
        assert Layer.Pass.value == 2
        assert Layer.Foreground.value == 3
        assert Layer.Overlay.value == 4

    def test_layer_lookup(self):
        assert Layer["Background"] == Layer.Background
        assert Layer(0) == Layer.Background
        assert Layer(4) == Layer.Overlay

    def test_origin_values(self):
        assert Origin.TopLeft.value == 0
        assert Origin.Centre.value == 1
        assert Origin.BottomRight.value == 9

    def test_loop_type_values(self):
        assert LoopType.LoopForever.value == 0
        assert LoopType.LoopOnce.value == 1


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------
class TestCommand:
    def test_basic_construction(self):
        cmd = Command("F", 0, 1000, 2000, [0.0, 1.0])
        assert cmd.type == "F"
        assert cmd.easing == 0
        assert cmd.start_time == 1000
        assert cmd.end_time == 2000
        assert cmd.params == [0.0, 1.0]

    def test_string_representation(self):
        cmd = Command("M", 1, 0, 500, [320.0, 240.0])
        s = str(cmd)
        assert "Command" in s
        assert "type=M" in s
        assert "easing=1" in s

    def test_with_string_params(self):
        cmd = Command("P", 0, 1000, 2000, ["H"])
        assert cmd.params == ["H"]


# ---------------------------------------------------------------------------
# LoopCommand
# ---------------------------------------------------------------------------
class TestLoopCommand:
    def test_default_construction(self):
        lc = LoopCommand(start_time=3000, loop_count=2)
        assert lc.start_time == 3000
        assert lc.loop_count == 2
        assert lc.commands == []
        assert lc.sub_max is None

    def test_with_sub_commands(self):
        sub = Command("F", 0, 0, 500, [0.0, 1.0])
        lc = LoopCommand(3000, 3, commands=[sub])
        assert len(lc.commands) == 1
        assert lc.commands[0].type == "F"


# ---------------------------------------------------------------------------
# SBObject / Sprite / Animation
# ---------------------------------------------------------------------------
class TestSBObject:
    def test_sprite_defaults(self):
        obj = Sprite(Layer.Background, Origin.Centre, "bg.jpg", Vector2(320, 240))
        assert obj.layer == Layer.Background
        assert obj.origin == Origin.Centre
        assert obj.filepath == "bg.jpg"
        assert obj.position == Vector2(320, 240)
        assert obj.commands == []
        assert obj.life_start == 0
        assert obj.life_end == 0

    def test_sprite_with_commands(self):
        cmd = Command("F", 0, 0, 1000, [0.0, 1.0])
        obj = Sprite(
            Layer.Pass, Origin.TopLeft, "sprite.png", Vector2(100, 200),
            commands=[cmd],
        )
        assert len(obj.commands) == 1

    def test_animation_defaults(self):
        anim = Animation(
            Layer.Foreground, Origin.BottomCentre, "frames/frame.png",
            Vector2(320, 240), frame_count=10, frame_delay=50.0,
        )
        assert anim.frame_count == 10
        assert anim.frame_delay == 50.0
        assert anim.loop_type == LoopType.LoopForever

    def test_animation_loop_once(self):
        anim = Animation(
            Layer.Overlay, Origin.Centre, "f.png", Vector2(0, 0),
            frame_count=5, frame_delay=100.0, loop_type=LoopType.LoopOnce,
        )
        assert anim.loop_type == LoopType.LoopOnce

    def test_sprite_is_sbobject(self):
        obj = Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        assert isinstance(obj, SBObject)

    def test_animation_is_sbobject(self):
        anim = Animation(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0))
        assert isinstance(anim, SBObject)


# ---------------------------------------------------------------------------
# ObjectState
# ---------------------------------------------------------------------------
class TestObjectState:
    def test_defaults(self):
        s = ObjectState()
        assert s.visible is False
        assert s.position == Vector2(0.0, 0.0)
        assert s.opacity == 1.0
        assert s.scale == 1.0
        assert s.scale_vec == Vector2(1.0, 1.0)
        assert s.rotation == 0.0
        assert s.r == 255.0
        assert s.g == 255.0
        assert s.b == 255.0
        assert s.flip_h is False
        assert s.flip_v is False
        assert s.additive is False
        assert s.image_path == ""
        assert s.frame_index == 0

    def test_custom_visible_position(self):
        s = ObjectState(visible=True, position=Vector2(320, 240))
        assert s.visible is True
        assert s.position == Vector2(320, 240)

    def test_color_channels(self):
        s = ObjectState(r=128, g=64, b=32)
        assert s.r == 128
        assert s.g == 64
        assert s.b == 32


# ---------------------------------------------------------------------------
# VideoObject
# ---------------------------------------------------------------------------
class TestVideoObject:
    def test_basic(self):
        vo = VideoObject(filepath="video.mp4", start_time=1000)
        assert vo.filepath == "video.mp4"
        assert vo.start_time == 1000
        assert vo.x_offset == 0
        assert vo.y_offset == 0

    def test_with_offsets(self):
        vo = VideoObject(filepath="v.mp4", start_time=2000, x_offset=10, y_offset=-5)
        assert vo.x_offset == 10
        assert vo.y_offset == -5

    def test_str_contains_info(self):
        vo = VideoObject("vid.mp4", 500)
        s = str(vo)
        assert "vid.mp4" in s
        assert "500" in s


# ---------------------------------------------------------------------------
# Storyboard
# ---------------------------------------------------------------------------
class TestStoryboard:
    def test_empty_storyboard(self):
        sb = Storyboard()
        assert sb.background_layer == []
        assert sb.fail_layer == []
        assert sb.pass_layer == []
        assert sb.foreground_layer == []
        assert sb.overlay_layer == []
        assert sb.video is None

    def test_is_empty_when_new(self):
        assert Storyboard().is_empty() is True

    def test_is_empty_with_video_only(self):
        sb = Storyboard()
        sb.video = VideoObject("v.mp4", 0)
        # is_empty returns True because no layer objects, but video exists
        # Actually, looking at the code:
        # return not any([layers]) and self.video is None
        # So a video alone does NOT make it non-empty... wait:
        # "not any([...]) and self.video is None"
        # If video is not None, the `and` is False, so overall is_empty() is False.
        assert sb.is_empty() is False

    def test_is_empty_with_object(self):
        sb = Storyboard()
        sb.add_object(Sprite(Layer.Pass, Origin.Centre, "x.png", Vector2(0, 0)))
        assert sb.is_empty() is False

    def test_add_object_to_correct_layer(self):
        sb = Storyboard()
        obj_bg = Sprite(Layer.Background, Origin.Centre, "bg.png", Vector2(0, 0))
        obj_pass = Sprite(Layer.Pass, Origin.Centre, "p.png", Vector2(0, 0))
        obj_fail = Sprite(Layer.Fail, Origin.Centre, "f.png", Vector2(0, 0))
        obj_fg = Sprite(Layer.Foreground, Origin.Centre, "fg.png", Vector2(0, 0))
        obj_ol = Sprite(Layer.Overlay, Origin.Centre, "ol.png", Vector2(0, 0))

        sb.add_object(obj_bg)
        sb.add_object(obj_pass)
        sb.add_object(obj_fail)
        sb.add_object(obj_fg)
        sb.add_object(obj_ol)

        assert sb.background_layer == [obj_bg]
        assert sb.pass_layer == [obj_pass]
        assert sb.fail_layer == [obj_fail]
        assert sb.foreground_layer == [obj_fg]
        assert sb.overlay_layer == [obj_ol]

    def test_merge_appends_objects(self):
        sb1 = Storyboard()
        sb2 = Storyboard()

        a = Sprite(Layer.Pass, Origin.Centre, "a.png", Vector2(0, 0))
        b = Sprite(Layer.Pass, Origin.Centre, "b.png", Vector2(0, 0))
        sb1.add_object(a)
        sb2.add_object(b)

        sb1.merge(sb2)
        assert len(sb1.pass_layer) == 2
        assert sb1.pass_layer[0] is a
        assert sb1.pass_layer[1] is b

    def test_merge_preserves_layer_separation(self):
        sb1 = Storyboard()
        sb2 = Storyboard()

        sb1.add_object(Sprite(Layer.Background, Origin.Centre, "bg1.png", Vector2(0, 0)))
        sb2.add_object(Sprite(Layer.Foreground, Origin.Centre, "fg2.png", Vector2(0, 0)))

        sb1.merge(sb2)
        assert len(sb1.background_layer) == 1
        assert len(sb1.foreground_layer) == 1
        assert len(sb1.pass_layer) == 0

    def test_merge_video_self_present(self):
        """Video on self should not be overwritten by other."""
        sb1 = Storyboard()
        sb2 = Storyboard()
        v1 = VideoObject("self.mp4", 0)
        v2 = VideoObject("other.mp4", 0)
        sb1.video = v1
        sb2.video = v2
        sb1.merge(sb2)
        assert sb1.video is v1

    def test_merge_video_self_none(self):
        """Video on other should be adopted when self has none."""
        sb1 = Storyboard()
        sb2 = Storyboard()
        v2 = VideoObject("other.mp4", 0)
        sb2.video = v2
        sb1.merge(sb2)
        assert sb1.video is v2

    def test_merge_returns_self(self):
        sb1 = Storyboard()
        sb2 = Storyboard()
        result = sb1.merge(sb2)
        assert result is sb1
