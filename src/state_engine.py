from typing import Optional, Tuple, List, Union
import math

from src.models import (
    SBObject,
    ObjectState,
    Sprite,
    Animation,
    LoopCommand,
    Command,
    LoopType,
    Storyboard,
    Vector2,
)
import src.easings as easings


class StateEngine:
    def __init__(self, storyboard: Storyboard):
        self.storyboard: Storyboard = storyboard
        self._calculate_lifetime()

    def _calculate_lifetime(self):
        """
        Calculate the lifetime for every object in the storyboard.
        Should be called after parsing the storyboard.
        """

        all_list = [
            self.storyboard.background_layer,
            self.storyboard.fail_layer,
            self.storyboard.pass_layer,
            self.storyboard.foreground_layer,
            self.storyboard.overlay_layer,
        ]

        for layer in all_list:
            for obj in layer:
                self._compute_object_lifetime(obj)

    def _compute_object_lifetime(self, obj: SBObject):
        min_t = float("inf")
        max_t = float("-inf")

        has_commands = False
        p_command_indices = []

        for idx, cmd in enumerate(obj.commands):
            has_commands = True
            if isinstance(cmd, Command):
                if cmd.start_time < min_t:
                    min_t = cmd.start_time
                if cmd.end_time > max_t:
                    max_t = cmd.end_time

                if cmd.type == "P":
                    p_command_indices.append(idx)
            elif isinstance(cmd, LoopCommand):
                sub_max = 0
                for sub_cmd in cmd.commands:
                    if sub_cmd.end_time > sub_max:
                        sub_max = sub_cmd.end_time

                cmd.sub_max = sub_max  # Store for later use

                lp_start = cmd.start_time
                lp_end = cmd.start_time + sub_max * cmd.loop_count

                if lp_start < min_t:
                    min_t = lp_start

                if lp_end > max_t:
                    max_t = lp_end

        if has_commands:
            obj.life_start = min_t
            obj.life_end = max_t
        else:
            obj.life_start = 0
            obj.life_end = 0

        if p_command_indices:
            # Check if start_time and end_time are the same
            for idx in p_command_indices:
                p_cmd = obj.commands[idx]
                if p_cmd.start_time == p_cmd.end_time:
                    # set the p_cmd time to object's lifetime
                    p_cmd.start_time = obj.life_start
                    p_cmd.end_time = obj.life_end

    def get_object_state(self, obj: SBObject, time: int) -> ObjectState | None:
        """
        Get the state of the object at a specific time by applying all relevant commands.
        """
        if time < obj.life_start or time > obj.life_end:
            return None

        state = ObjectState(
            visible=True, position=obj.position, opacity=1.0, image_path=obj.filepath
        )

        self._process_commands(obj.commands, time, state)

        if state.opacity < 0.001:
            return None  # Invisible due to opacity

        if isinstance(obj, Animation):
            self._update_animation_frame(obj, time, state)

        return state

    def _process_commands(
        self, commands: List[Union[Command, LoopCommand]], time: int, state: ObjectState
    ):
        for cmd in commands:
            if isinstance(cmd, LoopCommand):
                self._process_loop(cmd, time, state)
            elif isinstance(cmd, Command):
                if cmd.type == "P":
                    self._apply_parameter(cmd, state, time)
                    continue
                if time < cmd.start_time:
                    continue  # Command not started yet
                progress = 0.0
                if time > cmd.end_time:
                    progress = 1.0  # Command finished
                else:
                    duration = cmd.end_time - cmd.start_time
                    if duration == 0:
                        progress = 1.0
                    else:
                        normed_time = (time - cmd.start_time) / duration
                        progress = easings.apply_easing(cmd.easing, normed_time)

                self._apply_command_value(cmd, state, progress)

    def _process_loop(self, loop_cmd: LoopCommand, time: int, state: ObjectState):
        """
        Handle the loop commands
        """
        loop_duration = loop_cmd.sub_max
        if loop_duration is None:
            print("Error: LoopCommand missing sub_max value.")
            return

        total_duration = loop_duration * loop_cmd.loop_count

        start_abs = loop_cmd.start_time
        end_abs = start_abs + total_duration

        if time < start_abs or time > end_abs:
            return  # Outside loop time

        elapsed = time - start_abs
        # current_iteration = elapsed // loop_duration # Not used currently
        time_in_iteration = elapsed % loop_duration

        self._process_commands(loop_cmd.commands, time_in_iteration, state)

    def _apply_command_value(self, cmd: Command, state: ObjectState, progress: float):
        """
        Apply the command values to the object state based on the progress.
        """

        # params should be [start_value, end_value] or similar
        p = cmd.params

        if cmd.type == "F":  # Fade: [o1, o2]
            val = self._lerp(p[0], p[1], progress)
            state.opacity = val

        elif cmd.type == "M":  # Move: [x1, y1, x2, y2]
            state.position = Vector2(
                self._lerp(p[0], p[2], progress),
                self._lerp(p[1], p[3], progress),
            )

        elif cmd.type == "MX":  # MoveX: [x1, x2]
            state.position = Vector2(
                self._lerp(p[0], p[1], progress),
                state.position.y,
            )

        elif cmd.type == "MY":  # MoveY: [y1, y2]
            state.position = Vector2(
                state.position.x,
                self._lerp(p[0], p[1], progress),
            )

        elif cmd.type == "S":  # Scale: [s1, s2]
            scale = self._lerp(p[0], p[1], progress)
            state.scale_vec = Vector2(scale, scale)

        elif cmd.type == "V":  # Vector Scale: [w1, h1, w2, h2]
            state.scale_vec = Vector2(
                self._lerp(p[0], p[2], progress),
                self._lerp(p[1], p[3], progress),
            )
        elif cmd.type == "R":  # Rotate: [r1, r2]
            state.rotation = self._lerp(p[0], p[1], progress)

        elif cmd.type == "C":  # Color: [r1, g1, b1, r2, g2, b2]
            state.r = self._lerp(p[0], p[3], progress)
            state.g = self._lerp(p[1], p[4], progress)
            state.b = self._lerp(p[2], p[5], progress)

    def _apply_parameter(self, cmd: Command, state: ObjectState, time: int):
        param_type = cmd.params[0]
        if time > cmd.end_time:
            return  # Parameter commands have no interpolation
        if param_type == "H":
            state.flip_h = True
        elif param_type == "V":
            state.flip_v = True
        elif param_type == "A":
            state.additive = True

    def _lerp(self, start, end, t):
        return start + (end - start) * t

    def _update_animation_frame(self, obj: Animation, time: int, state: ObjectState):
        """
        Calculate the current frame of the animation based on time.
        """
        if obj.frame_count <= 0:
            return  # No frames to display

        run_time = time - obj.life_start
        if run_time < 0:
            run_time = 0

        total_frame_time = obj.frame_delay * obj.frame_count

        if obj.loop_type == LoopType.LoopOnce:
            if run_time >= total_frame_time:
                frame_index = obj.frame_count - 1
            else:
                frame_index = int(run_time / obj.frame_delay)

        else:  # LoopForever
            current_loop_time = run_time % total_frame_time
            frame_index = int(current_loop_time / obj.frame_delay)

        base, ext = obj.filepath.rsplit(".", 1)
        state.image_path = f"{base}{frame_index}.{ext}"
        state.frame_index = frame_index
