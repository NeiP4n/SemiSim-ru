#!/usr/bin/env bash
# Полная пересборка русского JAR из словаря и проверки.
#
# Порядок важен: классификация → словарь → патч → проверка патча.
# Причина: патч роняет игру, если в словарь попадёт строка-ключ, поэтому
# словарь проверяется ДО сборки.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

GAME="${SEMISIM_GAME_JAR:-$HOME/.local/share/Steam/steamapps/common/SemiSim/lib/app/SemiSim-2.2.1.jar}"
APP_DIR="${SEMISIM_APP_DIR:-$HOME/.local/share/Steam/steamapps/common/SemiSim/lib/app}"

if [[ ! -f "$GAME" ]]; then
    echo "не найден JAR игры: $GAME" >&2
    echo "укажи путь переменной SEMISIM_GAME_JAR" >&2
    exit 1
fi

echo "== 1. разбор байткода: границы инструкций =="
python3 tools/check_disasm.py "$GAME"

echo
echo "== 2. извлечение и классификация строк =="
python3 tools/extract.py --jar "$GAME" --app-dir "$APP_DIR" --out out/strings.json

echo
echo "== 3. классификация размечена верно? =="
python3 tools/check_classify.py
python3 tools/check_classify.py --self-test

echo
echo "== 4. словарь полон и не трогает ключи? =="
python3 tools/check_dict.py

echo
echo "== 5. шрифт 7x5 с кириллицей =="
python3 tools/font7x5.py

echo
echo "== 6. сборка русского JAR =="
python3 tools/patch.py --src "$GAME" --dict dict/translations.json \
    --out out/SemiSim-2.2.1-ru.jar --report out/patch_report.json \
    --font-class out/fontbuild/electrodynamics/util/Font7x5.class

echo
echo "== 7. русская справка рядом с JAR =="
python3 tools/help_install.py --help-dir help --target-dir out --report out/help_report.json

echo
echo "== 8. все переводы попали в JAR =="
python3 tools/patch.py --src x --dict dict/translations.json \
    --out out/SemiSim-2.2.1-ru.jar --verify

echo
echo "== 9. пакет перевода: только изменённые классы, без файлов игры =="
python3 tools/make_patch_jar.py

echo
echo "ИТОГ: JAR и пакет перевода собраны, все проверки зелёные:"
echo "  out/SemiSim-2.2.1-ru.jar  — полная русская копия игры (для сборки дистрибутива)"
echo "  out/ru-patch.jar          — только перевод, 260 КБ (классpath-подход)"
