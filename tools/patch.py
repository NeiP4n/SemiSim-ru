"""Сборка русского JAR из словаря перевода.

Заменяются только строковые константы классов пакета electrodynamics.
Ключи сохранений и настроек не трогаются: словарь проверяется до сборки,
а отчёт о заменах показывает, что именно изменилось.

Код возврата: 0 — успех, 1 — ошибка проверки или сборки.
"""

import argparse
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classfile  # noqa: E402

GAME_PACKAGE = "electrodynamics/"


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build(src_jar, dict_path, out_jar, report_path, verify_only=False, font_class=None):
    """Собрать патченный JAR или только проверить словарь по готовому файлу."""
    translations = load_json(dict_path)
    changed_total = 0
    touched_classes = []
    font_replaced = False
    # Строки, встречающиеся хотя бы в одном классе игры. Проверять «не найдено»
    # надо по объединению: одна строка может лежать в другом классе, и тогда
    # она уже переведена.
    found_anywhere = set()

    font_bytes = None
    if font_class and os.path.isfile(font_class):
        with open(font_class, "rb") as fh:
            font_bytes = fh.read()

    with zipfile.ZipFile(src_jar) as zin:
        with zipfile.ZipFile(out_jar, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                raw = zin.read(info.filename)
                if info.filename.endswith(".class") and info.filename.startswith(
                    GAME_PACKAGE
                ):
                    pool = classfile.parse(raw)
                    present = {value for _, value in pool.string_constants()}
                    found_anywhere |= {s for s in present if s in translations}
                    count = pool.replace_utf8(translations)
                    if count:
                        raw = pool.serialize()
                        changed_total += count
                        touched_classes.append(info.filename)
                    # класс шрифта заменяется целиком: в нём нет видимых строк,
                    # кириллица добавляется новыми глифами в карте
                    if font_bytes and info.filename.endswith(
                        "electrodynamics/util/Font7x5.class"
                    ):
                        raw = font_bytes
                        font_replaced = True
                        touched_classes.append(info.filename)
                # порядок записей и их метаданные сохраняем: игра читает
                # ресурсы по имени, а не по порядку
                zout.writestr(info, raw)

    missing = set(translations) - found_anywhere
    report = {
        "src_jar": src_jar,
        "out_jar": out_jar,
        "translations_in_dict": len(translations),
        "strings_replaced": changed_total,
        "classes_touched": len(touched_classes),
        "font_class_replaced": font_replaced,
        "touched_class_list": sorted(touched_classes),
        "not_found_in_game": sorted(missing),
    }
    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    return report


def verify(out_jar, dict_path, report):
    """Проверить, что в готовом JAR присутствуют русские переводы.

    Критерий: ни одна строка словаря не должна остаться в JAR в исходном
    виде — иначе часть перевода просто не применилась.
    """
    translations = load_json(dict_path)
    # Строки, которые решено оставить как есть (единицы, названия систем
    # единиц, имена шрифтов, HTML-скелеты): их перевод совпадает с оригиналом.
    expected_changed = {k for k, v in translations.items() if k != v}
    with zipfile.ZipFile(out_jar) as zf:
        remaining = set()
        found = set()
        for info in zf.infolist():
            if not (
                info.filename.endswith(".class")
                and info.filename.startswith(GAME_PACKAGE)
            ):
                continue
            pool = classfile.parse(zf.read(info.filename))
            values = {value for _, value in pool.string_constants()}
            for original, translation in translations.items():
                if translation in values:
                    found.add(original)
                # осталась непереведённой только та строка, которую меняли
                if original in values and original in expected_changed:
                    remaining.add(original)
    missing_translations = sorted(expected_changed - found)
    return {
        "present_in_jar": len(found),
        "unchanged_by_design": len(set(translations) - expected_changed),
        "still_untranslated": sorted(remaining),
        "translation_not_found_in_jar": missing_translations,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="оригинальный JAR игры")
    ap.add_argument("--dict", required=True, help="словарь перевода JSON")
    ap.add_argument("--out", required=True, help="куда собрать русский JAR")
    ap.add_argument("--report", default="out/patch_report.json")
    ap.add_argument(
        "--font-class",
        default=None,
        help="пересобранный Font7x5.class с кириллицей: подменяет класс целиком",
    )
    ap.add_argument(
        "--verify", action="store_true", help="не собирать, а проверить уже готовый JAR"
    )
    args = ap.parse_args()

    if args.verify:
        result = verify(args.out, args.dict, None)
        print(f"переводов найдено в JAR: {result['present_in_jar']}")
        print(f"оставлено как есть по решению: {result['unchanged_by_design']}")
        if result["still_untranslated"]:
            print(f"ОСТАЛИСЬ БЕЗ ПЕРЕВОДА: {len(result['still_untranslated'])}")
            for line in result["still_untranslated"][:20]:
                print(f"  {line!r}")
            return 1
        if result["translation_not_found_in_jar"]:
            print(f"ПЕРЕВОДЫ НЕ НАЙДЕНЫ: {len(result['translation_not_found_in_jar'])}")
            for line in result["translation_not_found_in_jar"][:20]:
                print(f"  {line!r}")
            return 1
        print("РЕЗУЛЬТАТ: зелёный — все переводы присутствуют в JAR")
        return 0

    report = build(
        args.src, args.dict, args.out, args.report, font_class=args.font_class
    )
    print(f"заменено строк: {report['strings_replaced']}")
    print(f"затронуто классов: {report['classes_touched']}")
    print(f"класс шрифта заменён: {report['font_class_replaced']}")
    if report["not_found_in_game"]:
        print(f"ВНИМАНИЕ: не найдено в игре {len(report['not_found_in_game'])}:")
        for line in report["not_found_in_game"][:20]:
            print(f"  {line!r}")
    print(f"собрано: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
