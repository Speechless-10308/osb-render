import os
from src.models import Storyboard, Sprite, Layer, Origin, Command, LoopCommand, Vector2
from src.state_engine import StateEngine


def test_manual_construction():
    print("=== Test 1: Manual Construction & Basic Interpolation ===")
    sb = Storyboard()

    # 创建一个 Sprite
    # 初始位置 (320, 240)
    obj = Sprite(Layer.Pass, Origin.Centre, "sb/test.png", Vector2(320, 240))

    # 1. Fade In: 1000ms -> 2000ms, 0 -> 1
    obj.commands.append(Command("F", 0, 1000, 2000, [0, 1]))

    # 2. Move: 2000ms -> 3000ms, (320, 240) -> (400, 300), Easing Out(1) -> QuadOut
    obj.commands.append(Command("M", 1, 2000, 3000, [320, 240, 400, 300]))

    # 3. Scale Loop: 从 3000ms 开始，循环 2 次
    #    子命令: 0-500ms Scale 1->1.5, 500-1000ms Scale 1.5->1
    loop = LoopCommand(3000, 2)
    loop.commands.append(Command("S", 0, 0, 500, [1, 1.5]))
    loop.commands.append(Command("S", 0, 500, 1000, [1.5, 1]))
    obj.commands.append(loop)

    sb.add_object(obj)

    # 初始化引擎
    engine = StateEngine(sb)

    # 测试点
    test_times = [
        500,  # Before start (Should be None)
        1000,  # Start Fade (Opacity 0)
        1500,  # Mid Fade (Opacity 0.5)
        2000,  # End Fade (Opacity 1), Start Move
        2500,  # Mid Move (Easing check)
        3000,  # End Move, Start Loop
        3250,  # Loop 1 Mid Scale Up
        3500,  # Loop 1 Peak
        4250,  # Loop 2 Mid Scale Up
        5000,  # Loop End
        5001,  # After Life (Should be None? Or hold last state?)
    ]

    print(f"Object Lifetime: {obj.life_start} -> {obj.life_end}")

    for t in test_times:
        state = engine.get_object_state(obj, t)
        if state:
            print(
                f"T={t}: Opacity={state.opacity:.2f}, Pos=({state.position.x:.1f}, {state.position.y:.1f}), Scale={state.scale_vec.x:.2f}"
            )
        else:
            print(f"T={t}: Object Invisible / None")


def test_parser_integration():
    print("\n=== Test 2: Parser Integration (Mock File String) ===")
    # 模拟一个简单的 .osb 文件内容
    # 包含简写和 P 命令
    file_content = """
[Events]
// Background layer
Sprite,Background,Centre,"bg.jpg",320,240
_F,0,0,1000,0,1
_M,0,1000,2000,320,240,320,480
_P,0,1000,2000,H
// Shorthand check: Fade out-in-out
_F,0,2000,4000,1,0,1,0
"""

    # 写入临时文件
    with open("tests/test_temp.osb", "w") as f:
        f.write(file_content)

    from src.parser import StoryboardParser

    parser = StoryboardParser()
    sb = parser.parse("tests/test_temp.osb")
    engine = StateEngine(sb)
    obj = sb.background_layer[0]
    print(f"Parsed Object Commands Count: {len(obj.commands)}")

    # 验证简写是否展开
    # F(2000-4000, 4 params) 应该产生 3 个命令段?
    # 1,0,1,0 -> 1->0, 0->1, 1->0. Total 3 segments.
    # 验证最后一条命令的结束时间是否正确
    # total duration = 2000, 3 segments -> each 666ms?

    last_cmd = obj.commands[-1]
    print(f"Last Command: {last_cmd}")

    # 检查 P 命令效果
    state_1500 = engine.get_object_state(obj, 1500)
    print(
        f"T=1500: FlipH={state_1500.flip_h}, Pos=({state_1500.position.x}, {state_1500.position.y})"
    )

    # 清理
    import os

    try:
        os.remove("tests/test_temp.osb")
    except:
        pass


def test_real_storyboard():
    osb_path = "tests\\UNDEAD CORPORATION - Everything will freeze (Ekoro).osb"
    from src.parser import StoryboardParser

    parser = StoryboardParser()
    sb = parser.parse(osb_path)
    engine = StateEngine(sb)

    print(sb)

    test_time = [0, 70000, 80000, 90000]
    for t in test_time:
        print(f"\n--- States at T={t} ---")
        for obj in sb.background_layer:
            state = engine.get_object_state(obj, t)
            if state:
                print(
                    f"BG Object: File={obj.filepath} Pos=({state.position.x}, {state.position.y}), Opacity={state.opacity} Scale=({state.scale})"
                )


if __name__ == "__main__":
    test_manual_construction()
    test_parser_integration()
    test_real_storyboard()
