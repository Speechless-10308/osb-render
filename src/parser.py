import os
from src.models import (
    Storyboard,
    SBObject,
    Sprite,
    Animation,
    Layer,
    Origin,
    Command,
    LoopCommand,
    LoopType,
    Vector2,
)
from typing import List, Optional, Union


class StoryboardParser:
    def __init__(self):
        self.storyboard = Storyboard()
        self.current_object: Optional[SBObject] = None
        self.current_loop: Optional[LoopCommand] = None

    def parse(self, filepath: str) -> Storyboard:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"The file {filepath} does not exist.")

        with open(filepath, "r", encoding="utf-8") as file:
            lines = file.readlines()

        is_events_section = False
        for line in lines:
            line = line.rstrip()

            if not line and line.startswith("//"):
                continue  # Skip empty lines and comments

            if line.startswith("["):
                if line == "[Events]":
                    is_events_section = True
                else:
                    is_events_section = False
                continue

            if is_events_section:
                self._parse_line(line)

        return self.storyboard

    def _parse_line(self, line: str):
        indent_level = 0

        while line.startswith("_") or line.startswith(" "):
            indent_level += 1
            line = line[1:]

        parts = line.split(",")

        if indent_level == 0:
            self._parse_object(parts)
        elif indent_level == 1:
            self._parse_command_l1(parts)
        elif indent_level == 2:
            self._parse_command_l2(parts)

    def _parse_object(self, parts: List[str]):
        object_type = parts[0].strip()

        if object_type not in ["Sprite", "Animation"]:
            return  # Unsupported object type

        try:
            layer = Layer[parts[1].strip()]
            origin = Origin[parts[2].strip()]
            filepath = parts[3].strip().strip('"')
            x = float(parts[4].strip())
            y = float(parts[5].strip())

            if object_type == "Sprite":
                storyboard_object = Sprite(
                    layer=layer,
                    origin=origin,
                    filepath=filepath,
                    position=Vector2(x, y),
                )
            elif object_type == "Animation":
                frame_count = int(parts[6].strip())
                frame_delay = int(parts[7].strip())
                loop_type = LoopType.LoopForever
                if len(parts) > 8:
                    # Optional loop type
                    try:
                        loop_type = LoopType[parts[8]]
                    except KeyError:
                        pass
                storyboard_object = Animation(
                    layer=layer,
                    origin=origin,
                    filepath=filepath,
                    position=Vector2(x, y),
                    frame_count=frame_count,
                    frame_delay=frame_delay,
                    loop_type=loop_type,
                )

            else:
                return  # Unsupported object type

            self.current_object = storyboard_object
            self.storyboard.add_object(storyboard_object)

        except Exception as e:
            print(f"Error parsing {parts}: {e}")
            self.current_object = None

    def _parse_command_l1(self, parts: List[str]):
        if not self.current_object:
            return  # No current object to attach commands to

        command_type = parts[0].strip()

        # handle the loop command
        if command_type == "L":
            try:
                start_time = int(parts[1].strip())
                loop_count = int(parts[2].strip())
                loop_command = LoopCommand(start_time=start_time, loop_count=loop_count)
                self.current_loop = loop_command
                self.current_object.commands.append(loop_command)
            except Exception as e:
                print(f"Error parsing loop command {parts}: {e}")
        elif command_type == "T":
            pass  # Trigger command, I think we can ignore it for now
        else:
            self.current_loop = None
            commands = self._parse_basic_command(parts)
            if commands:
                self.current_object.commands.extend(commands)

    def _parse_command_l2(self, parts: List[str]):
        if not self.current_loop:
            return  # No current loop to attach commands to

        commands = self._parse_basic_command(parts)
        if commands:
            self.current_loop.commands.extend(commands)

    def _parse_basic_command(self, parts: List[str]) -> List[Command]:
        got_commands: List[Command] = []

        try:
            event = parts[0]
            easing = int(parts[1])
            start_time = int(parts[2])

            end_time_str = parts[3] if len(parts) > 3 else ""
            if not end_time_str:
                end_time = start_time
            else:
                end_time = int(end_time_str)

            raw_params = parts[4:]
            params: List[Union[float, str]] = []

            if event == "P":
                # A, H, V commands have string parameters
                if raw_params:
                    params.append(raw_params[0])
                    return [Command(event, easing, start_time, end_time, params)]
            else:
                for p in raw_params:
                    if p:
                        params.append(float(p))

                # the fucking shorten commands!
                # F=Opacity(1), M=x,y(2), S=Scale(1), V=ScaleX,ScaleY(2), R=Angle(1), C=r,g,b(3)
                vars_count_map = {
                    "F": 1,
                    "S": 1,
                    "R": 1,
                    "MX": 1,
                    "MY": 1,
                    "M": 2,
                    "V": 2,
                    "C": 3,
                }

                if event not in vars_count_map:
                    print(f"Unknown command type: {event}")
                    return []

                vars_count = vars_count_map[event]
                total_params = len(params)

                # 2nd: start_params == end_params
                # something like:
                # `_(event),(easing),(starttime),(endtime),(value(s))` => `_(event),(easing),(starttime),(endtime),(value(s)),(value(s))`
                if total_params == vars_count:
                    params.extend(params[:])
                    total_params = len(params)

                # 1st: same duration for multiple params
                # something like:
                # `_(event),(easing),(starttime),(endtime),(value1),(value2),...,(valueN)`
                # will be
                # _(event),(easing),(starttime_of_first),(endtime_of_first),(value(s)_1),(value(s)_2)
                # _(event),(easing),((starttime_of_first) + (duration)),((endtime_of_first) + duration),(value(s)_2),(value(s)_3)
                # ...
                # _(event),(easing),((starttime_of_first) + (N-2)*duration),((endtime_of_first) + (N-2)*duration),(value(s)_(N-1)),(value(s)_N)
                if total_params < vars_count * 2:
                    return got_commands  # Not enough parameters

                state_count = total_params // vars_count
                commands_count = state_count - 1

                duration = end_time - start_time
                for i in range(commands_count):
                    curr_start_time = start_time + i * duration
                    curr_end_time = end_time + i * duration

                    start_idx = i * vars_count
                    end_idx = (i + 2) * vars_count  # python slice is exclusive

                    current_segment_params = params[start_idx:end_idx]
                    got_commands.append(
                        Command(
                            type=event,
                            easing=easing,
                            start_time=curr_start_time,
                            end_time=curr_end_time,
                            params=current_segment_params,
                        )
                    )
            return got_commands

        except Exception as e:
            print(f"Error parsing command '{parts}': {e}")
            return None


if __name__ == "__main__":
    file_path = "tests/x - xx (9ami).osb"
    parser = StoryboardParser()
    storyboard = parser.parse(file_path)
    print(storyboard)
