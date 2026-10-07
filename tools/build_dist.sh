#!/usr/bin/env bash
# Сборка дистрибутива для других людей: один файл setup.exe, внутри которого
# уже лежит весь перевод.
#
# Ключевое: в дистрибутив НЕ попадает ни одного файла игры. Установщик
# кладёт рядом с игрой пакет ru-patch.jar (55 изменённых классов, 260 КБ)
# и прописывает его первым в classpath — файлы игры остаются нетронутыми.
#
# Проверка после сборки: python3 tools/check_installer.py
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
cd "$HERE" || exit 1

DIST="$HERE/dist"
PATCH="out/ru-patch.jar"

if [[ ! -f "$PATCH" ]]; then
    echo "нет пакета перевода: $PATCH — сначала bash tools/build.sh" >&2
    exit 1
fi

# стираем только свою папку: dist/ общий с портативным набором
rm -r "$DIST/SemiSim-ru-setup" 2>/dev/null || true
rm -f "$DIST/SemiSim-ru-setup.zip"
mkdir -p "$DIST"

# 1. установщик: статическая сборка, чтобы не тянуть Visual C++ на чужую машину
# -mwindows: приложение с окном, а не с чёрной консолью. Без этого флага
# установщик открывает консольное окно, а MessageBoxA в нём не работает —
# пользователь видит мелькнувшую консоль вместо диалога.
WINFLAGS="-mwindows -O2 -static"

if command -v x86_64-w64-mingw32-gcc >/dev/null 2>&1; then
    x86_64-w64-mingw32-gcc $WINFLAGS -o "$DIST/setup.exe" src/setup.c -ladvapi32 -lshell32
else
    echo "нет mingw — берём уже собранный setup.exe из корня" >&2
    [[ -f setup.exe ]] || { echo "нет setup.exe: соберите вручную" >&2; exit 1; }
    cp setup.exe "$DIST/setup.exe"
fi

# 32-битная сборка, если нужен старый Windows
if command -v i686-w64-mingw32-gcc >/dev/null 2>&1; then
    i686-w64-mingw32-gcc $WINFLAGS -o "$DIST/setup-32.exe" src/setup.c -ladvapi32 -lshell32
fi

# установщик для Linux — тот же исходник, вдруг кому понадобится
if command -v gcc >/dev/null 2>&1; then
    gcc -O2 -o "$DIST/setup-linux" src/setup.c
fi

# 2. вшиваем перевод и справку внутрь каждого установщика
for f in setup.exe setup-32.exe setup-linux; do
    [[ -f "$DIST/$f" ]] || continue
    python3 tools/embed_payload.py \
        --exe "$DIST/$f" \
        --jar "$PATCH" \
        --help-dir help \
        --guide "$DIST/INSTALL-$f.txt" >/dev/null
done

# 3. проверяем: внутри только перевод, никаких файлов игры
for f in setup.exe setup-32.exe setup-linux; do
    [[ -f "$DIST/$f" ]] || continue
    python3 tools/check_installer.py --installer "$DIST/$f"
done

# 4. инструкция, продублированная текстом (внутри установщика она тоже есть)
cp "$DIST/INSTALL-setup.exe.txt" "$DIST/INSTALL.txt"

if command -v zip >/dev/null 2>&1; then
    # перечисляем файлы явно: zip по маске затянул бы в архив
    # портативный набор, который лежит в той же папке dist/
    (cd "$DIST" && zip -q9 "SemiSim-ru-setup.zip" \
        setup.exe setup-32.exe setup-linux INSTALL.txt)
    echo "архив: dist/SemiSim-ru-setup.zip"
    unzip -l "$DIST/SemiSim-ru-setup.zip" | tail -n +4 | head -n -2
fi

echo "дистрибутив: $DIST"
ls -la "$DIST"