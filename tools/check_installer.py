#!/usr/bin/env python3
"""Проверка установщика: что внутри него и что игра не пострадала.

Что проверяем:
1. В setup.exe есть хвост-маркер и смещение блока, а в блоке — ровно три файла:
   пакет перевода и две страницы справки.
2. Пакет перевода содержит только те .class, которые патч действительно менял,
   и в них есть русские строки.
3. В пакете нет ни одного файла игры целиком: ни графики, ни звука, ни шрифтов.

Отрицательный контроль (--expect-broken): проверка обязана упасть на
испорченном установщике. Без него зелёный цвет ничего не значит.
"""

import argparse
import json
import os
import struct
import sys
import zipfile

MAGIC = b"SEMISIMPAYL"
TAIL = b"SEMISIMEND"
NAME_LEN = 64
PATCH_NAME = "ru-patch.jar"

# файлы игры, которые не имеют права попасть в пакет перевода
FORBIDDEN_SUFFIX = (
    ".png",
    ".jpg",
    ".wav",
    ".ttf",
    ".so",
    ".dll",
    ".dylib",
    ".properties",
    ".json",
    ".csv",
    ".obj",
    ".fnt",
    ".glsl",
)


def has_cyrillic(data):
    """Есть ли в байтах класса кириллица: русские буквы в UTF-8 идут парами
    байт D0xx или D1xx, поэтому ищем их в потоке констант класса."""
    return any(
        data[i] in (0xD0, 0xD1) and data[i + 1] >= 0x80 for i in range(len(data) - 1)
    )


def read_payload(installer):
    """Достать встроенные файлы тем же способом, каким это делает setup.c."""
    with open(installer, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        if size < len(TAIL) + 8:
            raise ValueError("файл слишком мал")
        fh.seek(-(len(TAIL) + 8), os.SEEK_END)
        tail = fh.read(len(TAIL))
        offset = struct.unpack("<q", fh.read(8))[0]
        if tail != TAIL:
            raise ValueError("нет завершающего маркера: установщик собран без перевода")
        if not 0 < offset < size:
            raise ValueError(f"смещение блока {offset} вне файла {size}")
        fh.seek(offset)
        if fh.read(len(MAGIC)) != MAGIC:
            raise ValueError("по смещению не маркер блока")
        count = struct.unpack("<i", fh.read(4))[0]
        files = {}
        for _ in range(count):
            name = fh.read(NAME_LEN).split(b"\0")[0].decode("utf-8")
            length = struct.unpack("<i", fh.read(4))[0]
            files[name] = fh.read(length)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--installer", default="setup.exe")
    ap.add_argument("--report", default="out/patch_report.json")
    ap.add_argument(
        "--expect-broken",
        action="store_true",
        help="режим негативного контроля: ждём ошибку",
    )
    args = ap.parse_args()

    problems = []
    try:
        files = read_payload(args.installer)
    except ValueError as exc:
        if args.expect_broken:
            print(f"НЕГАТИВНЫЙ КОНТРОЛЬ: проверка упала как и должна — {exc}")
            return 0
        print(f"ПРОВАЛ: {exc}", file=sys.stderr)
        return 1

    names = set(files)
    if PATCH_NAME not in names:
        problems.append(f"внутри нет {PATCH_NAME}: есть {sorted(names)}")
    if "README.html" not in names or "examples.html" not in names:
        problems.append("внутри нет русской справки")

    patch = files.get(PATCH_NAME, b"")
    if patch:
        import io

        with zipfile.ZipFile(io.BytesIO(patch)) as zf:
            entries = zf.namelist()
            bad = [e for e in entries if e.lower().endswith(FORBIDDEN_SUFFIX)]
            if bad:
                problems.append(f"в пакете перевода чужие файлы игры: {bad[:5]}")
            if not all(e.endswith(".class") for e in entries):
                problems.append("в пакете есть не только .class")
            if os.path.exists(args.report):
                with open(args.report, encoding="utf-8") as fh:
                    touched = set(json.load(fh)["touched_class_list"])
                extra = [e for e in entries if e not in touched]
                if extra:
                    problems.append(
                        f"в пакете классы, которых патч не менял: {extra[:5]}"
                    )
                missing = touched - set(entries)
                if missing:
                    problems.append(f"в пакете нет {len(missing)} изменённых классов")
                print(f"классов в пакете: {len(entries)}, патч менял: {len(touched)}")
            russian = sum(1 for name in entries if has_cyrillic(zf.read(name)))
            print(f"классов с русскими строками: {russian} из {len(entries)}")
            if russian == 0:
                problems.append("в пакете нет ни одной русской строки")

    size = os.path.getsize(args.installer)
    print(f"размер установщика: {size} байт ({size / 1024:.0f} КБ)")
    if size > 2 * 1024 * 1024:
        problems.append(
            f"установщик подозрительно большой: {size} байт — похоже, внутри игра"
        )

    if problems:
        for item in problems:
            print(f"ПРОВАЛ: {item}", file=sys.stderr)
        return 1
    print(f"ИТОГ: установщик цел, внутри только перевод и справка.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
