#!/usr/bin/env bash
# Подмена JAR игры на русский: обычный запуск из Steam станет русским.
#
# Оригинал сохраняется рядом с расширением .orig и восстанавливается этим же
# скриптом с ключом --restore.
#
# Steam при «проверке целостности файлов» вернёт оригинал — тогда просто
# запустите скрипт заново.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
RU_JAR="$HERE/out/SemiSim-2.2.1-ru.jar"
GAME_DIR="${SEMISIM_GAME_DIR:-$HOME/.local/share/Steam/steamapps/common/SemiSim}"
APP_DIR="$GAME_DIR/lib/app"

# В classpath игры два файла с одинаковым именем: в app/ и в app/archive-tmp/.
# JVM берёт первый, но при замене только одного второй остаётся оригиналом,
# поэтому заменяем оба.
TARGETS=(
    "$APP_DIR/SemiSim-2.2.1.jar"
    "$APP_DIR/archive-tmp/SemiSim-2.2.1.jar"
)
HELP_FILES=(README.html examples.html)

restore() {
    local restored=0 target backup
    for target in "${TARGETS[@]}"; do
        backup="$target.orig"
        if [[ -f "$backup" ]]; then
            mv "$backup" "$target"
            echo "восстановлено: $target"
            restored=1
        fi
    done
    for name in "${HELP_FILES[@]}"; do
        [[ -f "$APP_DIR/$name.orig" ]] && mv "$APP_DIR/$name.orig" "$APP_DIR/$name"
    done
    if [[ "$restored" -eq 0 ]]; then
        echo "бэкапов не найдено: заменяли не мы" >&2
        return 1
    fi
    echo "Оригинал игры восстановлен."
    return 0
}

if [[ "${1:-}" == "--restore" ]]; then
    restore
    exit $?
fi

if [[ ! -f "$RU_JAR" ]]; then
    echo "не найден русский JAR: $RU_JAR" >&2
    echo "соберите его: bash tools/build.sh" >&2
    exit 1
fi

if [[ ! -d "$APP_DIR" ]]; then
    echo "не найдена папка игры: $APP_DIR" >&2
    echo "укажите путь переменной SEMISIM_GAME_DIR" >&2
    exit 1
fi

echo "Замена JAR игры на русский вариант"
echo "  папка игры: $APP_DIR"
echo

for target in "${TARGETS[@]}"; do
    if [[ ! -f "$target" ]]; then
        echo "нет файла: $target — пропускаю" >&2
        continue
    fi
    if [[ -f "$target.orig" ]]; then
        echo "бэкап уже есть, оригинал не перезаписываю: $target.orig"
    else
        cp -p "$target" "$target.orig"
        echo "бэкап оригинала: $target.orig"
    fi
    cp "$RU_JAR" "$target"
    echo "заменено: $target"
done

for name in "${HELP_FILES[@]}"; do
    if [[ -f "$HERE/help/$name" ]]; then
        [[ -f "$APP_DIR/$name.orig" ]] || cp -p "$APP_DIR/$name" "$APP_DIR/$name.orig" 2>/dev/null
        cp "$HERE/help/$name" "$APP_DIR/$name"
        echo "справка: $name"
    fi
done

echo
echo "Готово. Теперь обычный запуск SemiSim из Steam будет на русском."
echo
echo "Вернуть английский оригинал:"
echo "  bash tools/install_into_steam.sh --restore"
echo
echo "Если Steam вернул оригинал при проверке целостности — запустите скрипт заново."