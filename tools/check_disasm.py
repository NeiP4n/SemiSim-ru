"""Проверка, что разбор байткода идёт ровно по границам инструкций.

Оракул для codescan: если обход сбивается, он находит несуществующие опкоды
или не доходит до конца метода. Проверяется на всех методах всех классов игры.
"""

import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classfile  # noqa: E402
import codescan  # noqa: E402

GAME_PREFIX = "electrodynamics/"


def methods_of(pool):
    """Пары (длина, код) для всех методов класса."""
    data = pool.tail
    u2 = lambda off: struct.unpack(">H", data[off : off + 2])[0]
    pos = 6 + 2 + 2 * u2(6)

    def skip(offset):
        count = u2(offset)
        offset += 2
        codes = []
        for _ in range(count):
            offset += 6
            attrs = u2(offset)
            offset += 2
            for _ in range(attrs):
                name_index = u2(offset)
                length = struct.unpack(">I", data[offset + 2 : offset + 6])[0]
                target = pool.entries[name_index]
                if target and target[0] == 1:
                    if classfile.from_mutf8(target[1][2:]) == "Code":
                        codes.append(offset + 6)
                offset += 6 + length
        return offset, codes

    pos, _ = skip(pos)
    pos, code_offsets = skip(pos)
    result = []
    for attr in code_offsets:
        length = struct.unpack(">I", data[attr + 4 : attr + 8])[0]
        result.append((length, data[attr + 8 : attr + 8 + length]))
    return result


def check(jar_path):
    """Прогнать по всем методам игры; вернуть (всего, с ошибками, примеры)."""
    total, broken, samples = 0, 0, []
    with zipfile.ZipFile(jar_path) as zf:
        for info in zf.infolist():
            if not info.filename.startswith(GAME_PREFIX) or not info.filename.endswith(
                ".class"
            ):
                continue
            pool = classfile.parse(zf.read(info.filename))
            for length, code in methods_of(pool):
                total += 1
                # Критерий: инструкции покрывают код ровно до конца. Начало
                # последней инструкции не обязано совпадать с последним
                # байтом — у invokevirtual и putfield операнд занимает два байта.
                try:
                    end = codescan.code_end(code)
                    ok = end == len(code)
                    last = f"обход закончился на {end} из {len(code)}"
                except ValueError as exc:
                    # сбитый разбор — это красный результат, а не падение скрипта
                    ok, last = False, str(exc)
                if not ok:
                    broken += 1
                    if len(samples) < 5:
                        samples.append(f"{info.filename}: {last} (длина {length})")
    return total, broken, samples


def main():
    jar = (
        sys.argv[1]
        if len(sys.argv) > 1
        else (
            os.path.expanduser(
                "~/.local/share/Steam/steamapps/common/SemiSim/lib/app/SemiSim-2.2.1.jar"
            )
        )
    )
    total, broken, samples = check(jar)
    print(f"методов проверено: {total}")
    print(f"разобранных с ошибкой границ: {broken}")
    for line in samples:
        print(f"  {line}")
    if broken:
        print("РЕЗУЛЬТАТ: красный — разбор байткода негодный")
        return 1
    print("РЕЗУЛЬТАТ: зелёный — все методы разобраны по границам инструкций")
    return 0


if __name__ == "__main__":
    sys.exit(main())
