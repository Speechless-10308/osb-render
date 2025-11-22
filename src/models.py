from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Union


# Some enums used in models
class Layer(Enum):
    Background = 0
    Fail = 1
    Pass = 2
    Foreground = 3
    Overlay = 4


class Origin(Enum):
    TopLeft = 0
    Centre = 1
    CentreLeft = 2
    TopRight = 3
    BottomCentre = 4
    TopCentre = 5
    Custom = 6
    CentreRight = 7
    BottomLeft = 8
    BottomRight = 9


class LoopType(Enum):
    LoopForever = 0
    LoopOnce = 1


# Some commands classes
@dataclass
class Command:
    """
    Defines commands for osu! storyboard. Include Move(M), Scale(S), Rotate(R), Fade(F), Color(C), Parameter(P), ScaleVec(V).
    """

    type: str
    easing: int
    start_time: int
    end_time: int
    params: List[Union[float, str]]

    def __str__(self):
        return f"Command(type={self.type}, easing={self.easing}, start_time={self.start_time}, end_time={self.end_time}, params={self.params})\n"


@dataclass
class LoopCommand:
    """
    Defines the Loop(L) command for osu! storyboard.
    """

    start_time: int
    loop_count: int
    sub_max: Optional[int] = None
    commands: List["Command"] = field(default_factory=list)

    def __str__(self):
        return f"LoopCommand(start_time={self.start_time}, loop_count={self.loop_count}, commands={self.commands})\n"


# helper dataclasses for storyboard
@dataclass
class Vector2:
    x: float
    y: float

    def __eq__(self, value):
        if not isinstance(value, Vector2):
            return False
        return self.x == value.x and self.y == value.y

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        return Vector2(self.x * other, self.y * other)


# The element in storyboard and the storyboard itself
@dataclass
class SBObject:
    layer: Layer
    origin: Origin
    filepath: str
    position: Vector2
    commands: List[Union[Command, LoopCommand]] = field(default_factory=list)
    life_start: Optional[int] = 0
    life_end: Optional[int] = 0

    def __str__(self):
        return f"SBObject(layer={self.layer}, origin={self.origin}, filepath='{self.filepath}', position={self.position}, commands={self.commands})\n"


@dataclass
class Sprite(SBObject):
    pass


@dataclass
class Animation(SBObject):
    frame_count: int = 0
    frame_delay: float = 0
    loop_type: LoopType = LoopType.LoopForever


@dataclass
class ObjectState:
    visible: bool = False
    position: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    opacity: Optional[float] = 1.0
    scale: Optional[float] = 1.0
    scale_vec: Vector2 = field(default_factory=lambda: Vector2(1.0, 1.0))
    rotation: Optional[float] = 0.0

    r: Optional[int] = 255.0
    g: Optional[int] = 255.0
    b: Optional[int] = 255.0

    flip_h: bool = False
    flip_v: bool = False
    additive: bool = False

    # Animation only
    image_path: str = ""
    frame_index: int = 0


@dataclass
class Storyboard:
    background_layer: List[SBObject] = field(default_factory=list)
    fail_layer: List[SBObject] = field(default_factory=list)
    pass_layer: List[SBObject] = field(default_factory=list)
    foreground_layer: List[SBObject] = field(default_factory=list)
    overlay_layer: List[SBObject] = field(default_factory=list)

    def add_object(self, obj: SBObject):
        """
        Add the object to the appropriate layer in the storyboard.
        """
        target_layer = {
            Layer.Background: self.background_layer,
            Layer.Fail: self.fail_layer,
            Layer.Pass: self.pass_layer,
            Layer.Foreground: self.foreground_layer,
            Layer.Overlay: self.overlay_layer,
        }.get(obj.layer)
        if target_layer is not None:
            target_layer.append(obj)

    def __str__(self):
        return f"Storyboard:\nBackground: {self.background_layer}\nFail: {self.fail_layer}\nPass: {self.pass_layer}\nForeground: {self.foreground_layer}\nOverlay: {self.overlay_layer}\n"
