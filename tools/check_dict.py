"""Проверка словаря перевода перед сборкой патча.

Стoит на пути патча, потому что одна переведённая строка-ключ ломает чтение
сохранений у пользователя, а заметить это можно только потом, на его файлах.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
STRINGS = os.path.join(ROOT, "out", "strings.json")
DICT = os.path.join(ROOT, "dict", "translations.json")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check(dict_path=DICT, strings_path=STRINGS):
    """Вернуть (ошибки, сводка, длинные надписи)."""
    translations = load(dict_path)
    report = load(strings_path)
    visible = set(report["visible"])
    forbidden = set(report["forbidden"])
    errors = []

    for original in translations:
        if original in forbidden:
            errors.append(f"В СЛОВАРЕ ЗАПРЕЩЁННЫЙ КЛЮЧ: {original!r}")

    untranslated = sorted(visible - set(translations))
    for original in untranslated:
        errors.append(f"НЕ ПЕРЕВЕДЕНО: {original!r}")

    # перевод не должен ломать разметку и символы оригинала
    for original, translation in translations.items():
        if original == translation:
            continue
        if original.count("<b>") != translation.count("<b>"):
            errors.append(f"РАЗМЕТКА ПОТЕРЯНА: {original!r} → {translation!r}")
        for symbol in "ρϕΦχℰσηΩ≤≥":
            if original.count(symbol) != translation.count(symbol):
                errors.append(
                    f"СИМВОЛ ПОТЕРЯН {symbol!r}: {original!r} → {translation!r}"
                )

    # Длина перевода не проверяется как ошибка: текст рисует Swing, и обрезку
    # видно только на скриншоте живой игры. Здесь лишь предупреждение.
    long_labels = sorted(
        (len(v), k, v)
        for k, v in translations.items()
        if k != v and len(v) > 45 and "<" not in v
    )
    summary = (
        f"в словаре {len(translations)}, видимых строк {len(visible)}, "
        f"переведено {len(set(translations) & visible)}"
    )
    return errors, summary, long_labels


def main():
    errors, summary, long_labels = check()
    print(summary)
    if long_labels:
        print(
            f"предупреждение: длинных подписей {len(long_labels)} (обрезается только в Swing)"
        )
        for length, original, translation in long_labels[:5]:
            print(f"  {length} симв: {original!r} → {translation!r}")
    if errors:
        print(f"НАРУШЕНИЙ: {len(errors)}")
        for line in errors[:20]:
            print(f"  {line}")
        if len(errors) > 20:
            print(f"  ... ещё {len(errors) - 20}")
        return 1
    print("РЕЗУЛЬТАТ: зелёный — словарь полон и не трогает ключи")
    return 0


if __name__ == "__main__":
    sys.exit(main())
