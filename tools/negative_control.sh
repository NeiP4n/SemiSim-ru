#!/usr/bin/env bash
# Отрицательный контроль оракулов проверки.
#
# Оракул, который никогда не падает, не доказывает ничего: зелёный вывод
# такого оракула — мнение, а не факт. Здесь каждый оракул проверяется на
# заведомо испорченной КОПИИ данных и обязан из-за этого упасть.
#
# Копии делаются во временном каталоге: файлы проекта не трогаются.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
cd "$HERE" || exit 1

WORK="$(mktemp -d)"
trap 'rm -r "$WORK"' EXIT
FAILED=0

report() {
    if [[ "$1" == ok ]]; then
        echo "  ОРАКУЛ $2 ГОДЕН: $3"
    else
        echo "  ОРАКУЛ $2 НЕГОДЕН: $3"
        FAILED=1
    fi
}

echo "== отрицательный контроль OR-SELFTEST: классификация строк =="
# портим классификацию: объявляем ключ переводимым
python3 - "$WORK" <<'EOF'
import json, sys, os
work = sys.argv[1]
report = json.load(open('out/strings.json', encoding='utf-8'))
for key in ('theme', 'gui_material'):
    if key in report['forbidden']:
        report['forbidden'].remove(key)
    report['visible'].append(key)
json.dump(report, open(os.path.join(work, 'strings_bad.json'), 'w', encoding='utf-8'),
          ensure_ascii=False)
EOF
if python3 tools/check_classify.py "$WORK/strings_bad.json" >/dev/null 2>&1; then
    report bad OR-SELFTEST "испорченная классификация принята как правильная"
else
    report ok OR-SELFTEST "испорченную классификацию отверг"
fi

echo
echo "== отрицательный контроль OR-SELFTEST: словарь =="
# портим словарь: в словарь кладём строку-ключ и теряем перевод
python3 - "$WORK" <<'EOF'
import json, sys, os
work = sys.argv[1]
tr = json.load(open('dict/translations.json', encoding='utf-8'))
tr['theme'] = 'Тема'                      # ключ настройки в словаре
del tr['File']                              # потерянный перевод
json.dump(tr, open(os.path.join(work, 'translations_bad.json'), 'w', encoding='utf-8'),
          ensure_ascii=False)
EOF
if python3 - "$WORK/translations_bad.json" <<'EOF'
import sys
sys.argv = ['check_dict', sys.argv[1]]
import importlib.util
spec = importlib.util.spec_from_file_location('check_dict', 'tools/check_dict.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
errors, summary, _ = mod.check(dict_path=sys.argv[1])
raise SystemExit(1 if errors else 0)
EOF
then
    report bad OR-SELFTEST "испорченный словарь принят как годный"
else
    report ok OR-SELFTEST "испорченный словарь отверг"
fi

echo
echo "== отрицательный контроль OR-SELFTEST: границы инструкций =="
# портим таблицу длин опкодов: завышаем длину invokevirtual
if python3 - <<'EOF'
import sys
sys.path.insert(0, 'tools')
import codescan
codescan.CMP[0xB6] = 7
import importlib.util, os
spec = importlib.util.spec_from_file_location('check_disasm', 'tools/check_disasm.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
total, broken, _ = mod.check(os.path.expanduser(
    '~/.local/share/Steam/steamapps/common/SemiSim/lib/app/SemiSim-2.2.1.jar'))
raise SystemExit(1 if broken else 0)
EOF
then
    report bad OR-SELFTEST "сломанная таблица опкодов прошла проверку"
else
    report ok OR-SELFTEST "сломанная таблица опкодов отвергнута"
fi

echo
echo "== отрицательный контроль OR-VERIFY: патч собирается не из того =="
# проверяем, что патч-скрипт ловит JAR без единого перевода
if python3 tools/patch.py --src x --dict dict/translations.json \
    --out "$WORK/no_translations.jar" --verify >/dev/null 2>&1; then
    report bad OR-VERIFY "пустой JAR принят как собранный правильно"
else
    report ok OR-VERIFY "JAR без переводов отвергнут"
fi

echo
if [[ "$FAILED" -eq 0 ]]; then
    echo "ИТОГ: все оракулы поймали испорченные данные"
    exit 0
fi
echo "ИТОГ: хотя бы один оракул негоден"
exit 1
