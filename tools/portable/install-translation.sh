#!/usr/bin/env bash
# Russian translation installer for SemiSim, Linux, no exe needed.
# Copies the translation next to the game and puts it first on the classpath.
# No game file is replaced: SemiSim-2.2.1.jar stays original.
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
    echo "Game folder not found. Run: ./install-translation.sh /path/to/SemiSim" >&2
    exit 1
fi

APP="$GAME/lib/app"
echo "Game folder: $GAME"

if [[ ! -f "$HERE/ru-patch.jar" ]]; then
    echo "ru-patch.jar is missing next to this script" >&2
    exit 1
fi

cp -f "$HERE/ru-patch.jar" "$APP/ru-patch.jar"

for name in README.html examples.html; do
    [[ -f "$APP/$name" && ! -f "$APP/$name.orig" ]] && cp -f "$APP/$name" "$APP/$name.orig"
    cp -f "$HERE/$name" "$APP/$name"
done

# our classpath first, and exactly once
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
    echo "no app.classpath= line in SemiSim.cfg - leaving it untouched" >&2
    exit 1
fi

cat "$tmp" > "$CFG"
rm -f "$tmp"

echo "Done. The translation is active: start the game as usual."
echo "To go back to English: remove the ru-patch.jar line from SemiSim.cfg"
echo "and delete the file ru-patch.jar"