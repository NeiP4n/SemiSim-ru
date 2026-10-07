#!/usr/bin/env python3
"""Собрать пакет перевода: только те классы, которые патч изменил.

Зачем он нужен вместо русского JAR целиком: перевод работает через
classpath — JVM берёт первый найденный класс. Поэтому достаточно положить
рядом с игрой только изменённые классы, а игровой JAR вообще не трогать.
Пакет весит 260 КБ вместо 53 МБ и не содержит ни одного файла игры.

Вход:  out/SemiSim-2.2.1-ru.jar и out/patch_report.json
Выход: out/ru-patch.jar + отчёт out/patch_jar_report.json
"""

import argparse
import json
import os
import sys
import zipfile

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
    ".html",
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ru-jar", default="out/SemiSim-2.2.1-ru.jar")
    ap.add_argument("--report", default="out/patch_report.json")
    ap.add_argument("--out", default="out/ru-patch.jar")
    args = ap.parse_args()

    for path in (args.ru_jar, args.report):
        if not os.path.isfile(path):
            print(
                f"нет файла: {path} — сначала python3 tools/patch.py", file=sys.stderr
            )
            return 1

    with open(args.report, encoding="utf-8") as fh:
        touched = [
            c for c in json.load(fh)["touched_class_list"] if c.endswith(".class")
        ]

    # Фиксированное время входа: иначе zip зависит от часов сборки и две
    # сборки из одного словаря дают разные файлы — сравнивать их бессмысленно.
    with (
        zipfile.ZipFile(args.ru_jar) as src,
        zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as out,
    ):
        for name in touched:
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, src.read(name))

    problems = []
    with zipfile.ZipFile(args.out) as zf:
        entries = zf.namelist()
        if not all(e.endswith(".class") for e in entries):
            problems.append("в пакете есть не только .class")
        bad = [e for e in entries if e.lower().endswith(FORBIDDEN_SUFFIX)]
        if bad:
            problems.append(f"в пакете чужие файлы игры: {bad[:5]}")
        if set(entries) != set(touched):
            problems.append(
                f"состав не совпал с отчётом патча: {len(entries)} против {len(touched)}"
            )
        cyrillic = sum(
            1
            for name in entries
            if any(
                zf.read(name)[i] in (0xD0, 0xD1) and zf.read(name)[i + 1] >= 0x80
                for i in range(len(zf.read(name)) - 1)
            )
        )
        if cyrillic == 0:
            problems.append("в пакете нет ни одной русской строки")

    size = os.path.getsize(args.out)
    if size > 2 * 1024 * 1024:
        problems.append(f"пакет подозрительно большой: {size} байт")

    with open("out/patch_jar_report.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "patch_jar": args.out,
                "classes": len(touched),
                "bytes": size,
                "cyrillic_classes": cyrillic,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    print(f"пакет перевода: {args.out}")
    print(f"  классов: {len(touched)}")
    print(f"  с русскими строками: {cyrillic}")
    print(f"  размер: {size} байт ({size / 1024:.0f} КБ)")
    if problems:
        for item in problems:
            print(f"ПРОВАЛ: {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
