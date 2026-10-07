#!/usr/bin/env python3
"""Сборка установщика с переводом внутри.

Русские файлы приклеиваются к концу .exe блоком:
    "SEMISIMPAYL" | int32 число файлов | записи
    запись: имя[64] | int32 размер | байты

Установщик при запуске читает собственный файл с конца, находит блок и
кладёт файлы во временную папку. Распаковывать ничего не нужно: файлы
копируются как есть, поэтому разбор zip не требуется.

Формат текста и целые числа — всегда little endian, одинаково на всех
платформах, чтобы один и тот же .exe работал и в Windows, и при проверке
в Linux.
"""

import argparse
import os
import struct
import sys

MAGIC = b"SEMISIMPAYL"
# Хвост файла: завершающий маркер и смещение блока, чтобы установщик нашёл
# начало приклеенной части, не зная её длины.
TAIL = b"SEMISIMEND"
NAME_LEN = 64
GUIDE = """УСТАНОВКА РУССКОГО ПЕРЕВОДА SEMISIM
====================================

Всё нужное уже внутри этого файла. Ничего скачивать не нужно.

Как включить перевод
1. Закройте игру, если она запущена.
2. Запустите этот файл двойным кликом.
3. Программа сама найдёт папку игры SemiSim и спросит подтверждение.
4. Запускайте игру как обычно, через Steam. Интерфейс будет на русском.

Что произойдёт
- Рядом с игрой появится файл ru-patch.jar — это перевод, 260 КБ.
- В файле SemiSim.cfg появится одна строка: наш перевод стоит первым
  в списке загрузки классов, поэтому он перекрывает английский.
- Файлы игры не изменяются вообще: SemiSim-2.2.1.jar остаётся оригинальным.
- Руководство и каталог примеров станут русскими, исходные копии
  сохранятся с расширением .orig.

Вернуть английский
Запустите этот файл ещё раз и согласитесь на восстановление.
Программа уберёт файл перевода и вернёт SemiSim.cfg как было.

Почему игра не ломается при проверке Steam
Steam проверяет целостность только своих файлов. Наш файл он не знает,
а SemiSim-2.2.1.jar мы не трогаем — поэтому проверка проходит без
возврата к английскому. Достаточно повторного запуска установщика.

Тёмная тема
В игре она уже есть: Файл → Настройки → Тема интерфейса → FlatLaf Dark →
Применить. Выбор сохраняется и переживает перезапуск.

Что НЕ переведено
Надписи стандартных окон (Open, Cancel, Look In) берутся из ресурсов
самой Java, а не из файлов игры. Их перевод требует отдельной работы.

Требования
Windows 64 бит. Установленная игра SemiSim из Steam. Java не нужна:
игра запускается через Steam как обычно.

Игра SemiSim принадлежит её автору Brandon Li. Этот установщик содержит
только перевод и перевод справки — файлы игры не распространяются.
"""


def build(exe_path, jar_path, help_dir, guide_path=None, out_path=None):
    if not os.path.isfile(exe_path):
        print(f"нет установщика: {exe_path}", file=sys.stderr)
        return None
    if not os.path.isfile(jar_path):
        print(
            f"нет русского JAR: {jar_path} — сначала bash tools/build.sh",
            file=sys.stderr,
        )
        return None

    entries = [(os.path.basename(jar_path), jar_path)]
    for name in ("README.html", "examples.html"):
        path = os.path.join(help_dir, name)
        if os.path.isfile(path):
            entries.append((name, path))

    block = bytearray()
    block += MAGIC
    block += struct.pack("<i", len(entries))
    for name, path in entries:
        raw_name = name.encode("utf-8")[: NAME_LEN - 1]
        with open(path, "rb") as fh:
            data = fh.read()
        block += raw_name.ljust(NAME_LEN, b"\0")
        block += struct.pack("<i", len(data))
        block += data

    with open(exe_path, "rb") as fh:
        binary = fh.read()
    result = out_path or exe_path
    with open(result, "wb") as fh:
        fh.write(binary)
        fh.write(block)
        # Хвост: завершающий маркер и смещение начала блока — без них
        # установщик не найдёт встроенные файлы, не зная длины блока.
        fh.write(TAIL)
        fh.write(struct.pack("<q", len(binary)))

    report = {
        "installer": result,
        "installer_bytes": len(binary),
        "embedded_files": [
            {"name": n, "bytes": os.path.getsize(p)} for n, p in entries
        ],
        "total_bytes": len(binary) + len(block) + len(TAIL) + 8,
    }
    if guide_path:
        with open(guide_path, "w", encoding="utf-8") as fh:
            fh.write(GUIDE)
        report["guide"] = guide_path
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", default="setup.exe")
    ap.add_argument("--jar", default="out/SemiSim-2.2.1-ru.jar")
    ap.add_argument("--help-dir", default="help")
    ap.add_argument("--guide", default="УСТАНОВКА.txt")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    report = build(args.exe, args.jar, args.help_dir, args.guide, args.out)
    if report is None:
        return 1
    print(f"установщик: {report['installer']}")
    print(f"  программа: {report['installer_bytes']} байт")
    for item in report["embedded_files"]:
        print(f"  внутри: {item['name']} — {item['bytes']} байт")
    print(
        f"  всего: {report['total_bytes']} байт "
        f"({report['total_bytes'] / (1024 * 1024):.1f} МБ)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
