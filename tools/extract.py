"""Извлечение строк из JAR игры и разделение их на видимые и служебные.

Видимые строки переводить можно, служебные (ключи сохранений, настроек,
идентификаторы материалов) — нельзя: игра ищет их сравнением строк, и перевод
ломает чтение файлов и настроек.

Ключи берутся не из ручного списка, а из трёх независимых источников:
  1. имена полей в самих файлах сохранений и настроек игры;
  2. строки-идентификаторы из классов, которые эти файлы читают;
  3. имена констант перечислений, участвующих в сериализации.
"""

import argparse
import gzip
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classfile  # noqa: E402

# Строка без пробелов и спецсимволов: theme, imgsize_x, SEMI_N_TYPE, File
IDENT_RE = re.compile(r"^[A-Za-z0-9_.$:()<>/\\-]+$")

# ИМЯ КОНСТАНТЫ перечисления: SEMI_N_TYPE, AVERAGE_POTENTIAL, DELETEPROBE.
# У перечислений два поля — имя константы и отображаемое имя. Переводить
# можно только отображаемое: имя константы участвует в Enum.valueOf и
# сериализуется в файлы сохранений.
ENUM_CONST_RE = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")

# Настоящие имена констант перечислений длиннее двух букв и без смешения
# регистра. "OK" под правило попадал, хотя это надпись кнопки; "MU_ELECTRON"
# или "SEMI_N_TYPE" — настоящие имена.
ENUM_CONST_MIN_LEN = 3

# Имя файла с расширением: preferences.json, probedata.txt, workshop_item.semisim
FILENAME_RE = re.compile(r"^[\w-]+\.[A-Za-z0-9]+$")

# Значения, которые игра передаёт в API Swing или хранит как значение настройки.
# Их перевод не виден пользователю, но ломает работу программы:
#   North, South, East, West, Center — константы java.awt.BorderLayout,
#       игра передаёт их в Container.add(component, constraint)
#   none — CardLayout.NONE, normal — java.awt.Window.Type.NORMAL
#   SansSerif, Monospaced — логические имена шрифтов java.awt.Font
#   SI — значение ключа "units" в preferences.json; у перечисления Units нет
#       отдельного отображаемого имени, это и есть сохраняемое значение
SWING_API_VALUES = {
    "North",
    "South",
    "East",
    "West",
    "Center",
    "none",
    "normal",
    "SansSerif",
    "Monospaced",
    "SI",
}

# Единицы измерения и адреса: переводить их нельзя, но отличить их от
# подписи параметра по виду невозможно — "A/cm^2" это единица, а
# "Auger recomb. rate n [m^6/s]" подпись параметра с той же единицей внутри.
# Поэтому список собран из строк игры и проверен глазами: это пути,
# адреса, единицы СГС и HTML-скелеты. Подписи параметров сюда не входят.
UNIT_AND_PATH_STRINGS = {
    "(abV cm)/abA",
    "(cm V)/A",
    "(cm^2/(V s))",
    "(cm^2/(abV s))",
    "(cm^2/(statV s))",
    "(cm^2/s)",
    "(m^2/s)",
    "(statV cm)*statA",
    "</b><br>",
    "</body></html>",
    "</html>",
    "<html>",
    '<html><body style="',
    "A/cm",
    "A/cm^2",
    "A/m",
    "A/m^2",
    "A/(cm V)",
    "C/cm^2",
    "C/cm^3",
    "C/m^2",
    "C/m^3",
    "Documents/SemiSim",
    "J/cm",
    "J/cm^2",
    "J/cm^3",
    "J/m^3",
    "S/m",
    "V/cm",
    "V/m",
    "W/cm^2",
    "W/cm^3",
    "W/m^2",
    "W/m^3",
    "Wb/cm^2",
    "_tmp/image.png",
    "_tmp/workshop_item.semisim",
    "abA",
    "abA/cm^2",
    "abC",
    "abC/cm^2",
    "abC/cm^3",
    "abV",
    "abV/cm",
    "cm/s",
    "cm^2/s",
    "m/s",
    "m^2/s",
    "erg",
    "erg/(cm^2 s)",
    "erg/(cm^3 s)",
    "erg/(cm^3 s)",
    "erg/(K s)",
    "erg/(K s cm^3)",
    "erg/cm^3",
    "erg/s",
    "http://",
    "https://store.steampowered.com/app/4864110/Brandons_Semiconductor_Simulator/",
    "images/icon.png",
    "images/icons/",
    "images/thumbnails",
    "m^2/(V s)",
    "statA",
    "statA/cm",
    "statA/cm^2",
    "statC",
    "statC/cm^2",
    "statC/cm^3",
    "statT",
    "statV",
    "statV/cm",
    "statWb",
    "Wb",
    "dyn",
    "steam://url/CommunityFilePage/",
    "text/html",
    "x/y",
    "ε/ε₀",
    "μ/μ₀",
    # ВНИМАНИЕ: ссылки внутри видимых сообщений (окно «О программе»,
    # условия мастерской) сюда НЕ входят — это переводимый текст.
}


def save_keys_from_files(app_dir):
    """Ключи из настоящих файлов игры: .semisim (gzip+JSON) и preferences.json."""
    keys = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                keys.add(key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    examples = os.path.join(app_dir, "examples")
    for root, _dirs, files in os.walk(examples):
        for name in files:
            if not name.endswith(".semisim"):
                continue
            path = os.path.join(root, name)
            try:
                with gzip.open(path, "rb") as fh:
                    walk(json.loads(fh.read()))
            except (OSError, ValueError) as exc:
                print(f"пропущен {name}: {exc}", file=sys.stderr)
    prefs = os.path.join(app_dir, "preferences.json")
    if os.path.exists(prefs):
        try:
            with open(prefs) as fh:
                walk(json.load(fh))
        except (OSError, ValueError) as exc:
            print(f"пропущен preferences.json: {exc}", file=sys.stderr)
    return keys


def collect(jar_path):
    """Все строки игровых классов и строки, участвующие в сравнении."""
    strings = {}
    compared = set()
    with zipfile.ZipFile(jar_path) as zf:
        for info in zf.infolist():
            name = info.filename
            if not name.endswith(".class") or not name.startswith("electrodynamics/"):
                continue
            pool = classfile.parse(zf.read(name))
            for _, value in pool.string_constants():
                if value.strip():
                    strings.setdefault(value, set()).add(name)
            compared.update(pool.methods_using_string_comparison())
    return strings, compared


WORD_RE = re.compile(r"[A-Za-z]{2,}")


def classify(strings, compared, file_keys):
    """Разложить строки на видимые, служебные и обрывки форматирования.

    Служебной строка считается та, что участвует в сравнении в коде (ключ),
    лежит в файлах сохранений или настроек, либо не содержит ни одного слова
    из двух букв (обрывок форматирования вроде " = " или " E").
    """
    visible, forbidden, fragments, reasons = [], [], [], {}
    for value in sorted(strings):
        if value in SWING_API_VALUES:
            reasons[value] = "значение для API Swing или настройки"
            forbidden.append(value)
            continue
        if value in file_keys:
            reasons[value] = "ключ из файлов игры"
            forbidden.append(value)
            continue
        if value in compared:
            reasons[value] = "участвует в сравнении строк в коде"
            forbidden.append(value)
            continue
        if value in UNIT_AND_PATH_STRINGS:
            reasons[value] = "единица измерения, путь или адрес"
            forbidden.append(value)
            continue
        if value.startswith(".") or "\\" in value:
            reasons[value] = "путь или расширение"
            forbidden.append(value)
            continue
        if "%" in value:
            reasons[value] = "формат числа"
            forbidden.append(value)
            continue
        if FILENAME_RE.match(value):
            # Имя файла: preferences.json, probedata.txt. Игра открывает его по
            # этому имени, перевод сделает файл недоступным.
            reasons[value] = "имя файла"
            forbidden.append(value)
            continue
        if not WORD_RE.search(value):
            # ни одного слова из двух букв: символ, пробел, число, обрывок
            reasons[value] = "обрывок без слов"
            fragments.append(value)
            continue
        if (
            IDENT_RE.match(value)
            and len(value) >= ENUM_CONST_MIN_LEN
            and ENUM_CONST_RE.match(value)
        ):
            # Имя константы перечисления: переводится только отображаемое имя
            reasons[value] = "имя константы перечисления"
            forbidden.append(value)
            continue
        if IDENT_RE.match(value) and "_" in value:
            # Ключ служебного поля или контрола: gui_material, show_probearrows,
            # Eg_metal. Их передают в setActionCommand и сравнивают по имени,
            # поэтому переводить нельзя.
            reasons[value] = "ключ служебного поля"
            forbidden.append(value)
            continue
        if IDENT_RE.match(value) and not WORD_RE.search(value):
            # Служебное поле в одно слово: depth, T, nx, abV
            reasons[value] = "служебное поле"
            forbidden.append(value)
            continue
        visible.append(value)
    return visible, forbidden, fragments, reasons


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jar", required=True)
    ap.add_argument(
        "--app-dir",
        required=True,
        help="папка lib/app игры: нужна для ключей из её файлов",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    strings, compared = collect(args.jar)
    file_keys = save_keys_from_files(args.app_dir)
    visible, forbidden, fragments, reasons = classify(strings, compared, file_keys)

    report = {
        "jar": args.jar,
        "unique_strings": len(strings),
        "visible": visible,
        "forbidden": forbidden,
        "fragments": fragments,
        "forbidden_reasons": reasons,
        "file_keys_count": len(file_keys),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"уникальных строк: {len(strings)}")
    print(f"  видимых (переводимых): {len(visible)}")
    print(f"  служебных (запрещено): {len(forbidden)}")
    print(f"  обрывков форматирования (не трогаем): {len(fragments)}")
    print(f"  ключей прочитано из файлов игры: {len(file_keys)}")
    print(f"записано: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
