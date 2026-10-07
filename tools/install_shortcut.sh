#!/usr/bin/env bash
# Установка русской версии SemiSim в меню и на рабочий стол.
#
# Почему не подменяем файл внутри папки Steam: Steam проверяет целостность
# файлов и вернёт оригинал. Русский JAR лежит отдельно, а ярлык запускает его.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
JAR="$HERE/out/SemiSim-2.2.1-ru.jar"
ICON="/home/isako/.local/share/Steam/steamapps/common/SemiSim/lib/SemiSim.png"

if [[ ! -f "$JAR" ]]; then
    echo "не найден русский JAR: $JAR" >&2
    echo "соберите его командой: bash tools/build.sh" >&2
    exit 1
fi

APPS="$HOME/.local/share/applications"
DESKTOP="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Рабочий стол")"
mkdir -p "$APPS" "$DESKTOP"

ENTRY="[Desktop Entry]
Type=Application
Name=SemiSim (русский)
Comment=Симулятор полупроводников, русский интерфейс
Exec=$HERE/SemiSim-ru.sh
Path=$HERE
Icon=$ICON
Terminal=false
Categories=Game;Education;Science;
"

for target in "$APPS/semisim-ru.desktop" "$DESKTOP/SemiSim (русский).desktop"; do
    printf '%s' "$ENTRY" > "$target"
    chmod +x "$target" 2>/dev/null || true
    echo "ярлык: $target"
done

# меню приложений перечитываем, иначе значок не появится до перезагрузки
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi

echo
echo "ГОТОВО. Запускайте «SemiSim (русский)» с рабочего стола или из меню приложений."
echo "Обычный SemiSim в Steam остаётся английским — это оригинал игры, он не тронут."