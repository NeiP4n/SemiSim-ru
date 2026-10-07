"""Генератор класса Font7x5 с кириллицей.

Игра использует Font7x5 не для отрисовки, а как фильтр допустимых символов:
Controls.keyTyped проверяет каждый введённый символ через getCharacter и
отбрасывает те, которых нет в карте. Поэтому без кириллицы в метку зонда
нельзя ввести русский текст.

Класс пересобирается целиком, а не правится в байткоде: у него стабильный
публичный API (getCharacter, getPixel, printChar, поле FONT_MAP), а чтение
чужих глифов из исходного класса надёжнее, чем генерация байткода.

Формат глифа проверен на оригинале: 7 строк по 5 бит, бит 4 — левый столбец.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
GLYPHS_IN = os.path.join(ROOT, "out", "font7x5_glyphs.json")

# Кириллица в кодировке Java (номера кодовых точек)
CYRILLIC = [
    ("А", 0x0410),
    ("Б", 0x0411),
    ("В", 0x0412),
    ("Г", 0x0413),
    ("Д", 0x0414),
    ("Е", 0x0415),
    ("Ж", 0x0416),
    ("З", 0x0417),
    ("И", 0x0418),
    ("Й", 0x0419),
    ("К", 0x041A),
    ("Л", 0x041B),
    ("М", 0x041C),
    ("Н", 0x041D),
    ("О", 0x041E),
    ("П", 0x041F),
    ("Р", 0x0420),
    ("С", 0x0421),
    ("Т", 0x0422),
    ("У", 0x0423),
    ("Ф", 0x0424),
    ("Х", 0x0425),
    ("Ц", 0x0426),
    ("Ч", 0x0427),
    ("Ш", 0x0428),
    ("Щ", 0x0429),
    ("Ъ", 0x042A),
    ("Ы", 0x042B),
    ("Ь", 0x042C),
    ("Э", 0x042D),
    ("Ю", 0x042E),
    ("Я", 0x042F),
    ("а", 0x0430),
    ("б", 0x0431),
    ("в", 0x0432),
    ("г", 0x0433),
    ("д", 0x0434),
    ("е", 0x0435),
    ("ж", 0x0436),
    ("з", 0x0437),
    ("и", 0x0438),
    ("й", 0x0439),
    ("к", 0x043A),
    ("л", 0x043B),
    ("м", 0x043C),
    ("н", 0x043D),
    ("о", 0x043E),
    ("п", 0x043F),
    ("р", 0x0440),
    ("с", 0x0441),
    ("т", 0x0442),
    ("у", 0x0443),
    ("ф", 0x0444),
    ("х", 0x0445),
    ("ц", 0x0446),
    ("ч", 0x0447),
    ("ш", 0x0448),
    ("щ", 0x0449),
    ("ъ", 0x044A),
    ("ы", 0x044B),
    ("ь", 0x044C),
    ("э", 0x044D),
    ("ю", 0x044E),
    ("я", 0x044F),
    ("Ё", 0x0401),
    ("ё", 0x0451),
]

# Начертания кириллицы: 7 строк по 5 бит, '#' — пиксель.
# Рисунок задаётся текстом, чтобы его можно было прочитать глазами.
PATTERNS = {
    "А": ".###. #...# #...# ##### #...# #...# #...#",
    "Б": "####. #...# #...# ####. #...# #...# ####.",
    "В": "####. #...# #...# ####. #...# #...# ####.",
    "Г": "##### #.... #.... #.... #.... #.... #....",
    "Д": "..##. ..##. .#### ##### #...# #...# #####",
    "Е": "##### #.... #.... ####. #.... #.... #####",
    "Ж": "#...# #...# .###. ..#.. .###. #...# #...#",
    "З": "##### ....# ....# ..##. ....# ....# #####",
    "И": "#...# #...# #...# #...# #...# #...# #...#",
    "Й": ".#.#. #...# #...# #...# #...# #...# #...#",
    "К": "#...# #..#. #.#.. ##... #.#.. #..#. #...#",
    "Л": "..### .#... .#... .#... .#... .#... #####",
    "М": "#...# ##.## #.#.# #.#.# #...# #...# #...#",
    "Н": "#...# #...# #...# ##### #...# #...# #...#",
    "О": ".###. #...# #...# #...# #...# #...# .###.",
    "П": "##### #...# #...# #...# #...# #...# #...#",
    "Р": "####. #...# #...# ####. #.... #.... #....",
    "С": ".###. #...# #.... #.... #.... #...# .###.",
    "Т": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
    "У": "#...# #...# #...# .###. ....# .###. .###.",
    "Ф": "..#.. .###. ##### .###. ..#.. ..#.. ..#..",
    "Х": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
    "Ц": "#...# #...# #...# #...# ##### ....# ....#",
    "Ч": "#...# #...# #...# .#### ....# ....# ....#",
    "Ш": "#...# #...# #...# #...# #...# #...# #####",
    "Щ": "#...# #...# #...# #...# ##### ....# ....#",
    "Ъ": "###.. ..#.. ..#.. .###. #...# #...# .###.",
    "Ы": "#...# #...# #...# #..## #.#.# ##..# #...#",
    "Ь": "#.... #.... #.... ####. #...# #...# ####.",
    "Э": "##### ....# ..##. ....# ..##. ....# #####",
    "Ю": "#...# #...# #.### #.#.# #.### #...# #...#",
    "Я": ".###. #...# #...# .#### ....# ...#. .##..",
    "а": "..... ..... .###. ....# .#### #...# .####",
    "б": "...#. ..#.. .###. #...# ##### #...# #####",
    "в": "..... ..... ####. #...# ####. #...# ####.",
    "г": "..... ..... ##### #.... #.... #.... #....",
    "д": "..... ..... ..##. .#### ##### #...# #####",
    "е": "..... ..... .###. #...# ##### #.... .###.",
    "ж": "..... ..... #...# .###. ..#.. .###. #...#",
    "з": "..... ..... ##### ..##. ....# .###. ..#..",
    "и": "..... ..... #...# #...# #...# #...# #...#",
    "й": "..... ..#.. #...# #...# #...# #...# #...#",
    "к": "..... ..... #...# #..#. ##... #.#.. #..#.",
    "л": "..... ..... ..### .#... .#... .#... #####",
    "м": "..... ..... #...# ##.## #.#.# #...# #...#",
    "н": "..... ..... #...# #...# ##### #...# #...#",
    "о": "..... ..... .###. #...# #...# #...# .###.",
    "п": "..... ..... ##### #...# #...# #...# #...#",
    "р": "..... ..... ####. #...# ####. #.... #....",
    "с": "..... ..... .###. #...# #.... #...# .###.",
    "т": "..... ..#.. ##### ..#.. ..#.. ..#.. ..#..",
    "у": "..... ..... #...# #...# .#### ....# .###.",
    "ф": "..#.. .###. ##### .###. ..#.. ..#.. ..#..",
    "х": "..... ..... #...# .#.#. ..#.. .#.#. #...#",
    "ц": "..... ..... #...# #...# ##### ....# ....#",
    "ч": "..... ..... #...# #...# .#### ....# ....#",
    "ш": "..... ..... #...# #...# #...# #...# #####",
    "щ": "..... ..... #...# #...# ##### ....# ....#",
    "ъ": "..... ###.. ..#.. .###. #...# #...# .###.",
    "ы": "..... ..... #...# #..## #.#.# ##..# #...#",
    "ь": "..... ..... #.... ####. #...# #...# ####.",
    "э": "..... ..... ##### ..##. ....# ..##. #####",
    "ю": "..... ..... #.### #.#.# #.### #...# #...#",
    "я": "..... ..... .#### #...# .#### ....# #...#",
    "Ё": "..#.. .###. #.... ####. #.... #.... #####",
    "ё": "..#.. ..... .###. #...# ##### #.... .###.",
}


def pattern_to_rows(name):
    """Текстовый рисунок → семь байт глифа (бит 4 — левый столбец)."""
    if name not in PATTERNS:
        raise KeyError(f"нет начертания для {name!r}")
    cells = PATTERNS[name].split()
    if len(cells) != 7:
        raise ValueError(f"{name!r}: нужно 7 строк, получено {len(cells)}")
    rows = []
    for line in cells:
        if len(line) != 5:
            raise ValueError(f"{name!r}: в строке {line!r} не 5 знаков")
        value = 0
        for column, ch in enumerate(line):
            if ch == "#":
                value |= 1 << (4 - column)
        rows.append(value)
    return rows


JAVA_TEMPLATE = """// Сгенерировано tools/font7x5.py: шрифт игры с добавленной кириллицей.
// Формат глифа взят из оригинального класса electrodynamics.util.Font7x5:
// семь строк по пять бит, бит 4 — левый столбец. Латинские глифы (32..126)
// скопированы из оригинала без изменений, добавлены только русские буквы.
package electrodynamics.util;

import java.util.HashMap;
import java.util.Map;

public class Font7x5 {
    public static final Map<Character, byte[]> FONT_MAP = new HashMap<>();

    public Font7x5() {
    }

    public static byte[] getCharacter(char c) {
        return FONT_MAP.getOrDefault(Character.valueOf(c), null);
    }

    public static int getPixel(char c, int x, int y) {
        byte[] glyph = getCharacter(c);
        if (glyph == null || y < 0 || y >= glyph.length) {
            return 0;
        }
        return glyph[y] & (1 << (4 - x));
    }

    public static void printChar(char c) {
        byte[] glyph = getCharacter(c);
        if (glyph == null) {
            return;
        }
        for (int y = 0; y < glyph.length; y++) {
            StringBuilder line = new StringBuilder();
            for (int x = 4; x >= 0; x--) {
                line.append((glyph[y] & (1 << x)) != 0 ? '#' : ' ');
            }
            System.out.println(line);
        }
    }

    private static void put(int code, int r0, int r1, int r2, int r3, int r4, int r5, int r6) {
        FONT_MAP.put(Character.valueOf((char) code), new byte[]{(byte) r0, (byte) r1,
            (byte) r2, (byte) r3, (byte) r4, (byte) r5, (byte) r6});
    }

    static {
%s
    }
}
"""


def build_source(glyphs):
    lines = []
    for code, rows in sorted(glyphs.items()):
        char = chr(code)
        comment = char if char.isprintable() and not char.isspace() else "код %d" % code
        lines.append(
            f"        put({code}, {', '.join(str(r) for r in rows)}); // {comment}"
        )
    return JAVA_TEMPLATE % "\n".join(lines)


def main():
    with open(GLYPHS_IN, encoding="utf-8") as fh:
        glyphs = {int(k): v for k, v in json.load(fh).items()}

    # добавляем кириллицу к скопированной латинице
    added = 0
    for letter, code in CYRILLIC:
        if code not in glyphs:
            glyphs[code] = pattern_to_rows(letter)
            added += 1

    source = build_source(glyphs)
    work = os.path.join(ROOT, "out", "fontbuild")
    os.makedirs(work, exist_ok=True)
    src_path = os.path.join(work, "Font7x5.java")
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(source)

    jdk = None
    for candidate in (
        os.path.expanduser("~/.jdks/jdk-25"),
        os.path.expanduser("~/.jdks/jdk-21.0.12.1+1"),
    ):
        if os.path.exists(os.path.join(candidate, "bin", "javac")):
            jdk = candidate
            break
    if not jdk:
        print("не найден javac: нужен JDK для сборки класса шрифта", file=sys.stderr)
        return 1

    result = subprocess.run(
        [
            os.path.join(jdk, "bin", "javac"),
            "-encoding",
            "UTF-8",
            "-source",
            "8",
            "-target",
            "8",
            "-nowarn",
            "-d",
            work,
            src_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout + result.stderr, file=sys.stderr)
        return 1

    # метка (version 50) нужна, чтобы приняла JVM 8, как у остальных классов игры
    major_path = os.path.join(work, "electrodynamics", "util", "Font7x5.class")
    raw = open(major_path, "rb").read()
    patched = raw[:4] + bytes([0, 50]) + raw[6:]  # major 52 -> 50, как у игры
    open(major_path, "wb").write(patched)

    report = {
        "latin_glyphs_copied": len(glyphs) - added,
        "cyrillic_glyphs_added": added,
        "total_glyphs": len(glyphs),
        "class_file": major_path,
        "class_size": len(patched),
    }
    with open(
        os.path.join(ROOT, "out", "font_report.json"), "w", encoding="utf-8"
    ) as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"латиница скопирована: {report['latin_glyphs_copied']}")
    print(f"кириллица добавлена: {report['cyrillic_glyphs_added']}")
    print(f"всего глифов: {report['total_glyphs']}")
    print(f"класс собран: {major_path} ({report['class_size']} байт)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
