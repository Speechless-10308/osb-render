"""Unit tests for src/parser.py — StoryboardParser for .osu/.osb files."""

import os
import tempfile
import pytest
from src.parser import StoryboardParser
from src.models import (
    Storyboard, Sprite, Animation, VideoObject,
    Layer, Origin, LoopType, Command, LoopCommand, Vector2,
)


def _write_temp_osb(content: str) -> str:
    """Helper: write content to a temp .osb file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".osb", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------
class TestFileHandling:
    def test_file_not_found(self):
        parser = StoryboardParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path/file.osb")

    def test_empty_file(self):
        path = _write_temp_osb("")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.is_empty() is True
        finally:
            os.unlink(path)

    def test_no_events_section(self):
        path = _write_temp_osb("[General]\nAudioFilename: test.mp3\n")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.is_empty() is True
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Comments and blank lines
# ---------------------------------------------------------------------------
class TestCommentsAndBlanks:
    def test_comments_are_skipped(self):
        path = _write_temp_osb("""
[Events]
// This is a comment
Sprite,Background,Centre,"bg.jpg",320,240
// Another comment
_F,0,0,1000,0,1
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert len(sb.background_layer) == 1
        finally:
            os.unlink(path)

    def test_blank_lines_are_skipped(self):
        path = _write_temp_osb("""
[Events]

Sprite,Background,Centre,"bg.jpg",320,240

_F,0,0,1000,0,1

""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert len(sb.background_layer) == 1
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Sprite parsing
# ---------------------------------------------------------------------------
class TestSpriteParsing:
    def test_basic_sprite(self):
        path = _write_temp_osb("""
[Events]
Sprite,Background,Centre,"bg.jpg",320,240
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert len(sb.background_layer) == 1
            obj = sb.background_layer[0]
            assert isinstance(obj, Sprite)
            assert obj.layer == Layer.Background
            assert obj.origin == Origin.Centre
            assert obj.filepath == "bg.jpg"
            assert obj.position == Vector2(320, 240)
        finally:
            os.unlink(path)

    def test_sprite_with_quotes_in_path(self):
        """Filepath with surrounding quotes should be stripped."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,TopLeft,"path/to/image.png",100,200
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.pass_layer[0].filepath == "path/to/image.png"
        finally:
            os.unlink(path)

    def test_sprite_on_all_layers(self):
        path = _write_temp_osb("""
[Events]
Sprite,Background,Centre,"bg.png",0,0
Sprite,Fail,Centre,"fail.png",0,0
Sprite,Pass,Centre,"pass.png",0,0
Sprite,Foreground,Centre,"fg.png",0,0
Sprite,Overlay,Centre,"ol.png",0,0
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert len(sb.background_layer) == 1
            assert len(sb.fail_layer) == 1
            assert len(sb.pass_layer) == 1
            assert len(sb.foreground_layer) == 1
            assert len(sb.overlay_layer) == 1
        finally:
            os.unlink(path)

    def test_sprite_negative_position(self):
        path = _write_temp_osb("""
[Events]
Sprite,Foreground,Centre,"x.png",-100,-200
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.foreground_layer[0].position == Vector2(-100, -200)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Animation parsing
# ---------------------------------------------------------------------------
class TestAnimationParsing:
    def test_basic_animation(self):
        path = _write_temp_osb("""
[Events]
Animation,Pass,Centre,"frames/f.png",320,240,8,50
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert len(sb.pass_layer) == 1
            anim = sb.pass_layer[0]
            assert isinstance(anim, Animation)
            assert anim.frame_count == 8
            assert anim.frame_delay == 50.0
            assert anim.loop_type == LoopType.LoopForever  # default
        finally:
            os.unlink(path)

    def test_animation_with_loop_type(self):
        path = _write_temp_osb("""
[Events]
Animation,Foreground,BottomLeft,"f.png",0,0,4,100,LoopOnce
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            anim = sb.foreground_layer[0]
            assert isinstance(anim, Animation)
            assert anim.loop_type == LoopType.LoopOnce
        finally:
            os.unlink(path)

    def test_animation_invalid_loop_type_falls_back(self):
        """Invalid loop type name should not crash — defaults to LoopForever."""
        path = _write_temp_osb("""
[Events]
Animation,Background,Centre,"f.png",0,0,4,100,InvalidType
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            anim = sb.background_layer[0]
            assert anim.loop_type == LoopType.LoopForever
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Unknown object types
# ---------------------------------------------------------------------------
class TestUnknownObjectTypes:
    def test_unknown_object_type_is_skipped(self):
        path = _write_temp_osb("""
[Events]
UnknownType,Background,Centre,"x.png",0,0
Sprite,Background,Centre,"y.png",0,0
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            # Only the Sprite should be parsed; UnknownType skipped
            assert len(sb.background_layer) == 1
            assert sb.background_layer[0].filepath == "y.png"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Video event parsing
# ---------------------------------------------------------------------------
class TestVideoParsing:
    def test_video_event_by_name(self):
        path = _write_temp_osb("""
[Events]
Video,1000,"video.mp4",10,-5
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.video is not None
            assert sb.video.filepath == "video.mp4"
            assert sb.video.start_time == 1000
            assert sb.video.x_offset == 10
            assert sb.video.y_offset == -5
        finally:
            os.unlink(path)

    def test_video_event_by_numeric_code(self):
        path = _write_temp_osb("""
[Events]
1,2000,"vid.mp4",0,0
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.video is not None
            assert sb.video.filepath == "vid.mp4"
            assert sb.video.start_time == 2000
        finally:
            os.unlink(path)

    def test_video_event_missing_fields_defaults(self):
        path = _write_temp_osb("""
[Events]
Video,0,"v.mp4"
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.video is not None
            assert sb.video.x_offset == 0
            assert sb.video.y_offset == 0
        finally:
            os.unlink(path)

    def test_video_does_not_become_sprite(self):
        """Video events should NOT be added as sprites."""
        path = _write_temp_osb("""
[Events]
Video,0,"v.mp4"
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.is_empty() is False  # video present
            assert len(sb.background_layer) == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Basic command parsing (no shorthand)
# ---------------------------------------------------------------------------
class TestBasicCommandParsing:
    def test_fade_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_F,0,1000,2000,0,1
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmds = sb.pass_layer[0].commands
            assert len(cmds) == 1
            cmd = cmds[0]
            assert cmd.type == "F"
            assert cmd.easing == 0
            assert cmd.start_time == 1000
            assert cmd.end_time == 2000
            assert cmd.params == [0.0, 1.0]
        finally:
            os.unlink(path)

    def test_move_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_M,0,0,500,0,0,320,240
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "M"
            assert cmd.params == [0.0, 0.0, 320.0, 240.0]
        finally:
            os.unlink(path)

    def test_rotate_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_R,0,0,1000,0,3.14159
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "R"
            assert cmd.params == [0.0, 3.14159]
        finally:
            os.unlink(path)

    def test_color_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_C,0,0,500,255,255,255,128,64,32
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "C"
            assert cmd.params == [255.0, 255.0, 255.0, 128.0, 64.0, 32.0]
        finally:
            os.unlink(path)

    def test_scale_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_S,0,0,1000,1,2
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "S"
            assert cmd.params == [1.0, 2.0]
        finally:
            os.unlink(path)

    def test_scale_vec_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_V,0,0,500,1,1,2,0.5
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "V"
            assert cmd.params == [1.0, 1.0, 2.0, 0.5]
        finally:
            os.unlink(path)

    def test_move_x_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_MX,0,0,100,0,320
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "MX"
            assert cmd.params == [0.0, 320.0]
        finally:
            os.unlink(path)

    def test_move_y_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_MY,0,0,100,0,240
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "MY"
            assert cmd.params == [0.0, 240.0]
        finally:
            os.unlink(path)

    def test_parameter_command(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_P,0,1000,2000,H
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.type == "P"
            assert cmd.params == ["H"]
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Shorthand expansion
# ---------------------------------------------------------------------------
class TestShorthandExpansion:
    def test_start_only_shorthand(self):
        """Start-only shorthand: values duplicated for end."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_F,0,0,1000,0.5
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            # 1 param given → duplicated → [0.5, 0.5]
            assert cmd.params == [0.5, 0.5]
        finally:
            os.unlink(path)

    def test_multi_segment_shorthand(self):
        """Multiple value pairs with equal duration → sequential commands."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_F,0,0,1000,0,1,0
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmds = sb.pass_layer[0].commands
            # 3 params: 0,1,0 → 2 segments: 0→1 (0–1000), 1→0 (1000–2000)
            assert len(cmds) == 2
            assert cmds[0].start_time == 0
            assert cmds[0].end_time == 1000
            assert cmds[0].params == [0.0, 1.0]
            assert cmds[1].start_time == 1000
            assert cmds[1].end_time == 2000
            assert cmds[1].params == [1.0, 0.0]
        finally:
            os.unlink(path)

    def test_move_shorthand_multi_segment(self):
        """M command with 6 params (3 positions) → 2 segments."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_M,0,0,500,0,0,320,240,640,480
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmds = sb.pass_layer[0].commands
            assert len(cmds) == 2
            assert cmds[0].params == [0.0, 0.0, 320.0, 240.0]
            assert cmds[1].params == [320.0, 240.0, 640.0, 480.0]
            assert cmds[0].end_time == 500
            assert cmds[1].start_time == 500
            assert cmds[1].end_time == 1000
        finally:
            os.unlink(path)

    def test_insufficient_params_yields_no_commands(self):
        """If total_params < vars_count*2 (and != vars_count), no commands should be produced."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_M,0,0,500,320,240,100
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            # M needs at least 4 params (x1,y1,x2,y2) OR 2 params (start-only shorthand).
            # 3 params: != vars_count(2) → no duplication, then 3 < 4 → no commands
            assert len(sb.pass_layer[0].commands) == 0
        finally:
            os.unlink(path)

    def test_fade_four_params_three_segments(self):
        """4 Fade params (1,0,1,0) → 3 segments."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_F,0,0,1000,1,0,1,0
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmds = sb.pass_layer[0].commands
            assert len(cmds) == 3
            assert cmds[0].params == [1.0, 0.0]  # 1→0
            assert cmds[1].params == [0.0, 1.0]  # 0→1
            assert cmds[2].params == [1.0, 0.0]  # 1→0
        finally:
            os.unlink(path)

    def test_unknown_command_type_returns_empty(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_ZZ,0,0,100,1,2
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            # Unknown command type → no commands added
            assert len(sb.pass_layer[0].commands) == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Loop command parsing
# ---------------------------------------------------------------------------
class TestLoopParsing:
    def test_basic_loop(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_L,3000,2
__F,0,0,500,0,1
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmds = sb.pass_layer[0].commands
            assert len(cmds) == 1
            assert isinstance(cmds[0], LoopCommand)
            loop = cmds[0]
            assert loop.start_time == 3000
            assert loop.loop_count == 2
            assert len(loop.commands) == 1
            assert loop.commands[0].type == "F"
        finally:
            os.unlink(path)

    def test_loop_with_multiple_sub_commands(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_L,0,3
__F,0,0,500,0,1
__S,0,0,500,1,2
__R,0,0,500,0,1.57
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            loop = sb.pass_layer[0].commands[0]
            assert len(loop.commands) == 3
        finally:
            os.unlink(path)

    def test_commands_after_loop_are_top_level(self):
        """Commands after the loop block should be at indent level 1 (top-level)."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_L,0,2
__F,0,0,500,0,1
_F,0,0,1000,0,1
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmds = sb.pass_layer[0].commands
            assert len(cmds) == 2  # one loop, one top-level command
            assert isinstance(cmds[0], LoopCommand)
            assert isinstance(cmds[1], Command)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Trigger command (T) — ignored
# ---------------------------------------------------------------------------
class TestTriggerCommand:
    def test_trigger_is_ignored(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_T,TriggerName,0,1000
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            # Trigger commands are silently skipped
            assert len(sb.pass_layer[0].commands) == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------
class TestVariableSubstitution:
    def test_basic_variable(self):
        path = _write_temp_osb("""
[Variables]
$color=255,255,255
[Events]
Sprite,Pass,Centre,"x.png",0,0
_C,0,0,1000,$color,128,64,32
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            # $color should be replaced with "255,255,255"
            # Then the command gets split as 255,255,255,128,64,32 → 3 segments
            # Actually that's 6 color params = 2 segments
            assert cmd.params[0] == 255.0
            assert cmd.params[1] == 255.0
            assert cmd.params[2] == 255.0
        finally:
            os.unlink(path)

    def test_multiple_variables(self):
        path = _write_temp_osb("""
[Variables]
$x=320
$y=240
[Events]
Sprite,Pass,Centre,"x.png",0,0
_M,0,0,1000,0,0,$x,$y
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            cmd = sb.pass_layer[0].commands[0]
            assert cmd.params[2] == 320.0
            assert cmd.params[3] == 240.0
        finally:
            os.unlink(path)

    def test_variable_in_object_line(self):
        path = _write_temp_osb("""
[Variables]
$file=bg.jpg
[Events]
Sprite,Background,Centre,"$file",320,240
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.background_layer[0].filepath == "bg.jpg"
        finally:
            os.unlink(path)

    def test_no_variables_section(self):
        """Parser should work fine without any [Variables] section."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_F,0,0,1000,0,1
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert len(sb.pass_layer) == 1
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Indent-based parsing (spaces and underscores)
# ---------------------------------------------------------------------------
class TestIndentParsing:
    def test_space_indent(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
 F,0,0,1000,0,1
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert len(sb.pass_layer[0].commands) == 1
        finally:
            os.unlink(path)

    def test_mixed_indent_chars(self):
        """Multiple underscore and space prefixes accumulate indent level."""
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_L,0,2
__F,0,0,500,0,1
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            loop = sb.pass_layer[0].commands[0]
            assert isinstance(loop, LoopCommand)
            assert len(loop.commands) == 1
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Gibberish / error recovery
# ---------------------------------------------------------------------------
class TestErrorRecovery:
    def test_malformed_object_does_not_crash(self):
        """Malformed object line should be caught and skipped."""
        path = _write_temp_osb("""
[Events]
Sprite,NotAnEnum,Centre,"x.png",abc,def
Sprite,Pass,Centre,"y.png",0,0
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            # The bad line fails, the good line succeeds
            assert len(sb.pass_layer) == 1
            assert sb.pass_layer[0].filepath == "y.png"
        finally:
            os.unlink(path)

    def test_malformed_command_does_not_crash(self):
        path = _write_temp_osb("""
[Events]
Sprite,Pass,Centre,"x.png",0,0
_M,0,not_a_number,500,0,0,320,240
""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            # Should not crash; may have 0 commands due to parse error
            assert len(sb.pass_layer) == 1
        finally:
            os.unlink(path)

    def test_empty_parts_list(self):
        path = _write_temp_osb("""
[Events]

""")
        try:
            parser = StoryboardParser()
            sb = parser.parse(path)
            assert sb.is_empty() is True
        finally:
            os.unlink(path)
