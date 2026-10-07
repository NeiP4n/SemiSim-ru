#!/usr/bin/env bash
# Установка русского перевода SemiSim без установщика — для Linux.
# Копирует пакет перевода в папку игры и прописывает его первым в classpath.
# Файлы игры не заменяются: SemiSim-2.2.1.jar остаётся оригинальным.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME="${1:-}"
MARKER="lib/app/SemiSim.cfg"

if [[ -z "$GAME" ]]; then
    for candidate in \
        "$HOME/.local/share/Steam/steamapps/common/SemiSim" \
        "$HOME/.steam/steam/steamapps/common/SemiSim" \
        "$HOME/.steam/root/steamapps/common/SemiSim" \
        "${XDG_DATA_HOME:-$HOME/.local/share}/Steam/steamapps/common/SemiSim"
    do
        [[ -f "$candidate/$MARKER" ]] && { GAME="$candidate"; break; }
    done
fi

if [[ -z "$GAME" || ! -f "$GAME/$MARKER" ]]; then
    echo "Папка игры не найдена. Запустите так: ./install-translation.sh /путь/к/SemiSim" >&2
    exit 1
fi

APP="$GAME/lib/app"
echo "Папка игры: $GAME"

if [[ ! -f "$HERE/ru-patch.jar" ]]; then
    echo "нет файла ru-patch.jar рядом со скриптом" >&2
    exit 1
fi

cp -f "$HERE/ru-patch.jar" "$APP/ru-patch.jar"

for name in README.html examples.html; do
    [[ -f "$APP/$name" && ! -f "$APP/$name.orig" ]] && cp -f "$APP/$name" "$APP/$name.orig"
    cp -f "$HERE/$name" "$APP/$name"
done

# наш classpath первым, и ровно один раз
CFG="$APP/SemiSim.cfg"
tmp="$(mktemp)"
inserted=0
while IFS= read -r line; do
    case "$line" in
        *ru-patch.jar*) continue ;;
    esac
    if [[ $inserted -eq 0 && "$line" == app.classpath=* ]]; then
        printf 'app.classpath=$APPDIR/ru-patch.jar\n'
        inserted=1
    fi
    printf '%s\n' "$line"
done < "$CFG" > "$tmp"

if [[ $inserted -eq 0 ]]; then
    rm -f "$tmp"
    echo "в SemiSim.cfg не найдено ни одной строки app.classpath= — не трогаю" >&2
    exit 1
fi

cat "$tmp" > "$CFG"
rm -f "$tmp"

echo "Готово. Перевод включён: запускайте игру как обычно."
echo "Вернуть английский: удалите из SemiSim.cfg строку с ru-patch.jar и файл ru-patch.jar"