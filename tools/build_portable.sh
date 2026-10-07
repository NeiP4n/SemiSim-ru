#!/usr/bin/env bash
# Портативный набор: файлы для копирования в папку игры + скрипты установки.
#
# В отличие от setup.exe здесь нет программы установщика — только сам перевод
# и два скрипта (bat и sh), которые его копируют. Кому нужен zip без
# установщика или ручное копирование — берёт этот архив.
#
# Тексты кодируются в Windows-1251: cmd и «Блокнот» портят UTF-8.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

PATCH="out/ru-patch.jar"
SRC="tools/portable"
DIST="$HERE/dist"
OUT="$DIST/SemiSim-ru-portable"

if [[ ! -f "$PATCH" ]]; then
    echo "нет пакета перевода: $PATCH — сначала bash tools/build.sh" >&2
    exit 1
fi

rm -r "$OUT" 2>/dev/null || true
mkdir -p "$OUT"

cp "$PATCH" "$OUT/ru-patch.jar"
cp help/README.html "$OUT/README.html"
cp help/examples.html "$OUT/examples.html"

# тексты и bat — в Windows-1251
python3 - "$SRC" "$OUT" <<'PY'
import pathlib, sys

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
# символы, которых нет в Windows-1251: заменяем на ASCII, иначе кодирование падает
REPLACED = {"→": "->", "—": "-", "…": "...", "«": '"', "»": '"', "•": "*"}


def to_cp1251(text: str) -> str:
    for bad, good in REPLACED.items():
        text = text.replace(bad, good)
    return text


for name in ("ПРОСТО-СКОПИРУЙ.txt", "Установить-перевод.bat"):
    raw = to_cp1251((src / name).read_text(encoding="utf-8"))
    (out / name).write_bytes(raw.replace("\n", "\r\n").encode("cp1251"))
    print(f"  {name} - Windows-1251, {len(raw)} символов")
PY

cp "$SRC/установить-перевод.sh" "$OUT/установить-перевод.sh"
chmod +x "$OUT/установить-перевод.sh"

# проверяем состав архива
rm -f "$DIST/SemiSim-ru-portable.zip"
(cd "$OUT" && zip -qr9 "../SemiSim-ru-portable.zip" .)
python3 tools/check_portable.py --zip "$DIST/SemiSim-ru-portable.zip"

echo
echo "портативный набор: $OUT"
ls -la "$OUT"