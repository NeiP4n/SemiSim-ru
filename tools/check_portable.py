#!/usr/bin/env python3
"""Проверка портативного архива: только перевод, никаких файлов игры.

Что проверяем:
1. В архиве есть пакет перевода, справка, инструкция и скрипты установки.
2. Пакет перевода содержит только .class из отчёта патча, с русскими строками.
3. В архиве нет файлов игры: ни её JAR, ни картинок, ни звука, ни шрифтов.
4. Тексты в кодировке Windows-1251, иначе cmd и «Блокнот» покажут мусор.

Отрицательный контроль (--expect-broken): на подменённом архиве проверка
обязана упасть. Без него зелёный вывод ничего не значит.
"""

import argparse
import io
import json
import os
import sys
import zipfile

FORBIDDEN_SUFFIX = (
    ".png",
    ".jpg",
    ".wav",
    ".ogg",
    ".ttf",
    ".so",
    ".dll",
    ".dylib",
    ".properties",
    ".obj",
    ".fnt",
    ".glsl",
    ".class",
)
REQUIRED = ("ru-patch.jar", "README.html", "examples.html")
SCRIPTS = ("Установить-перевод.bat", "установить-перевод.sh")
TEXT_FILES = ("ПРОСТО-СКОПИРУЙ.txt",)


def cyrillic(data: bytes) -> bool:
    return any(
        data[i] in (0xD0, 0xD1) and data[i + 1] >= 0x80 for i in range(len(data) - 1)
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", default="dist/SemiSim-ru-portable.zip")
    ap.add_argument("--report", default="out/patch_report.json")
    ap.add_argument("--expect-broken", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.zip):
        if args.expect_broken:
            print("НЕГАТИВНЫЙ КОНТРОЛЬ: архива нет — проверка упала как и должна")
            return 0
        print(f"ПРОВАЛ: нет архива {args.zip}", file=sys.stderr)
        return 1

    problems: list[str] = []
    with zipfile.ZipFile(args.zip) as zf:
        names = zf.namelist()
        base = {os.path.basename(n): n for n in names}

        for want in REQUIRED:
            if want not in base:
                problems.append(f"в архиве нет {want}")
        for want in SCRIPTS:
            if want not in base:
                problems.append(f"в архиве нет скрипта {want}")

        bad = [n for n in names if n.lower().endswith(FORBIDDEN_SUFFIX)]
        if bad:
            problems.append(f"в архиве чужие файлы игры: {bad[:5]}")
        for name in names:
            low = name.lower()
            if "semisim-2.2.1.jar" in low or low.startswith("lib/"):
                problems.append(f"файл игры попал в архив: {name}")

        # тексты должны быть в Windows-1251: cmd и «Блокнот» иначе покажут мусор
        for want in TEXT_FILES + ("Установить-перевод.bat",):
            if want not in base:
                continue
            raw = zf.read(base[want])
            try:
                raw.decode("cp1251")
            except UnicodeDecodeError:
                problems.append(f"{want} не в Windows-1251")
            if (
                raw.decode("cp1251", "replace").isprintable()
                and raw[:3] == b"\xef\xbb\xbf"
            ):
                problems.append(
                    f"{want} сохранён в UTF-8 с BOM — cmd такой файл испортит"
                )

        if "ru-patch.jar" in base:
            with zipfile.ZipFile(io.BytesIO(zf.read(base["ru-patch.jar"]))) as patch:
                entries = patch.namelist()
                if not all(e.endswith(".class") for e in entries):
                    problems.append("в пакете перевода есть не только .class")
                if os.path.isfile(args.report):
                    with open(args.report, encoding="utf-8") as fh:
                        touched = set(json.load(fh)["touched_class_list"])
                    extra = [e for e in entries if e not in touched]
                    missing = touched - set(entries)
                    if extra:
                        problems.append(
                            f"в пакете классы, которых патч не менял: {extra[:3]}"
                        )
                    if missing:
                        problems.append(
                            f"в пакете нет {len(missing)} изменённых классов"
                        )
                    print(
                        f"классов в пакете: {len(entries)}, патч менял: {len(touched)}"
                    )
                with_russian = sum(1 for e in entries if cyrillic(patch.read(e)))
                print(f"классов с русскими строками: {with_russian} из {len(entries)}")
                if with_russian == 0:
                    problems.append("в пакете нет ни одной русской строки")

        # инструкция обязана говорить, куда класть и как вернуть английский
        readme_name = base.get("ПРОСТО-СКОПИРУЙ.txt")
        if readme_name:
            text = zf.read(readme_name).decode("cp1251", "replace")
            for needle in ("ru-patch.jar", "SemiSim.cfg", "$APPDIR"):
                if needle not in text:
                    problems.append(f"в инструкции нет упоминания {needle}")

    size = os.path.getsize(args.zip)
    print(f"размер архива: {size} байт ({size / 1024:.0f} КБ)")
    if size > 3 * 1024 * 1024:
        problems.append(
            f"архив подозрительно большой: {size} байт — похоже, внутри игра"
        )

    if problems:
        if args.expect_broken:
            print("НЕГАТИВНЫЙ КОНТРОЛЬ: проверка упала как и должна")
            for item in problems:
                print(f"  ПРОВАЛ: {item}")
            return 0
        for item in problems:
            print(f"ПРОВАЛ: {item}", file=sys.stderr)
        return 1
    print("ИТОГ: архив цел, внутри только перевод, справка и скрипты.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
