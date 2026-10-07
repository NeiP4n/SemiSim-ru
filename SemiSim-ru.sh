#!/usr/bin/env bash
# Запуск SemiSim с русским интерфейсом.
#
# Отдельный скрипт нужен по двум причинам:
#   1. Файлы игры в папке Steam не меняются: Steam проверяет целостность и
#      вернёт оригинал. Русский JAR лежит рядом, в этой папке.
#   2. Нужен JDK 25: JavaFX внутри игры собран под class file version 68,
#      на JDK 21 игра падает с UnsupportedClassVersionError.
#   3. Нужен SteamAppId: без него игра вызывает SteamAPI.restartAppIfNecessary
#      и завершается с кодом 0, выглядя так, будто не запустилась.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="$HERE/out/SemiSim-2.2.1-ru.jar"

if [[ ! -f "$JAR" ]]; then
    echo "не найден русский JAR: $JAR" >&2
    echo "соберите его: tools/build.sh" >&2
    exit 1
fi

find_jdk() {
    local candidate home_dir
    # Домашний каталог берём у владельца скрипта, а не из $HOME: игра может
    # запускаться с подменённым HOME, и тогда поиск по $HOME/.jdks провалится.
    home_dir="$(cd "$HERE" && getent passwd "$(id -un)" | cut -d: -f6)"
    [[ -z "$home_dir" ]] && home_dir="$HOME"
    for candidate in "$home_dir/.jdks/jdk-25" "$home_dir/.jdks"/*25* \
                     /usr/lib/jvm/*25* /opt/*jdk*25*; do
        if [[ -x "$candidate/bin/java" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

if ! JAVA_HOME="$(find_jdk)"; then
    echo "не найден JDK 25: нужен для запуска этой игры" >&2
    echo "подсказка: JavaFX в игре собран под class file version 68," >&2
    echo "         JDK 21 и ниже игру не запустят" >&2
    exit 1
fi

export SteamAppId=4864110
exec "$JAVA_HOME/bin/java" -jar "$JAR" "$@"
