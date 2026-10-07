#!/usr/bin/env bash
# Установка русского перевода SemiSim: выбираете папку игры — скрипт делает всё сам.
#
# Запускается двойным кликом. Если запустить из терминала без графического
# диалога, папку можно указать аргументом: ./setup_ru.sh /путь/к/SemiSim
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RU_JAR="$HERE/out/SemiSim-2.2.1-ru.jar"
BACKUP_SUFFIX=".orig"

msg() { printf '%s\n' "$*"; }
fail() { printf '%s\n' "$*" >&2; exit 1; }

# --- поиск игры -------------------------------------------------------------
# Папка игры: <библиотека>/steamapps/common/SemiSim, внутри нужен lib/app
is_game_dir() {
    [[ -f "$1/lib/app/SemiSim-2.2.1.jar" ]]
}

find_game_dir() {
    local roots=() vdf path
    for path in "$HOME/.local/share/Steam/steamapps/common/SemiSim" \
                "$HOME/.steam/steam/steamapps/common/SemiSim"; do
        [[ -d "$path" ]] && roots+=("$path")
    done
    # дополнительные библиотеки Steam перечислены в libraryfolders.vdf
    # полем "path" внутри каждой секции библиотеки
    vdf="$HOME/.steam/steam/steamapps/libraryfolders.vdf"
    if [[ -f "$vdf" ]]; then
        while read -r path; do
            [[ -n "$path" && "$path" == /* ]] || continue
            [[ "$path" == "$HOME" ]] && continue
            [[ -d "$path/steamapps/common/SemiSim" ]] && roots+=("$path/steamapps/common/SemiSim")
        done < <(sed -nE 's/^[[:space:]]*"path"[[:space:]]+"(\/[^"]*)".*/\1/p' "$vdf")
    fi
    for path in "${roots[@]}"; do
        is_game_dir "$path" && { echo "$path"; return 0; }
    done
    return 1
}

# --- диалог выбора ----------------------------------------------------------
ask_dir_gui() {
    local title text start
    title="Установка русского перевода SemiSim"
    text="Выберите папку игры SemiSim\n(в ней должен быть файл lib/app/SemiSim-2.2.1.jar)"
    start="${1:-$HOME}"
    if command -v zenity >/dev/null 2>&1; then
        zenity --file-selection --directory --title="$title" \
               --text="$text" --filename="$start/" 2>/dev/null
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --getexistingdirectory "$start" "$title" "$text" 2>/dev/null
    else
        fail "Нет диалога выбора папки. Запустите: $0 /путь/к/SemiSim"
    fi
}

confirm_gui() {
    local text="$1"
    if command -v zenity >/dev/null 2>&1; then
        zenity --question --text="$text" --width=460 >/dev/null 2>&1
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --yesno "$text" >/dev/null 2>&1
    else
        read -r -p "$text [y/N] " answer
        [[ "$answer" == y || "$answer" == Y ]]
    fi
}

info_gui() {
    local text="$1"
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --text="$text" --width=520 >/dev/null 2>&1
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --msgbox "$text" >/dev/null 2>&1
    else
        msg "$text"
    fi
}

# --- основное ---------------------------------------------------------------
GAME_DIR="${1:-}"

if [[ ! -f "$RU_JAR" ]]; then
    fail "Русская версия ещё не собрана.
Сначала выполните в папке проекта: bash tools/build.sh
(появится файл out/SemiSim-2.2.1-ru.jar)"
fi

if [[ -z "$GAME_DIR" ]]; then
    if GAME_DIR="$(find_game_dir)"; then
        msg "Игра найдена: $GAME_DIR"
    else
        msg "Игра не найдена в библиотеках Steam. Выберите папку вручную."
        GAME_DIR="$(ask_dir_gui)" || fail "Папка не выбрана — ничего не изменено."
    fi
fi

[[ -d "$GAME_DIR" ]] || fail "Такой папки нет: $GAME_DIR"
if ! is_game_dir "$GAME_DIR"; then
    # возможно, выбрали вложенную папку lib/app
    if is_game_dir "$(dirname "$GAME_DIR")"; then
        GAME_DIR="$(dirname "$GAME_DIR")"
    else
        fail "Это не папка игры SemiSim.
Ожидалось: $GAME_DIR/lib/app/SemiSim-2.2.1.jar
Выбрано: $GAME_DIR/lib/app/SemiSim-2.2.1.jar — нет"
    fi
fi
GAME_DIR="$(cd "$GAME_DIR" && pwd)"

APP_DIR="$GAME_DIR/lib/app"
RESTORE=""
if [[ -f "$APP_DIR/SemiSim-2.2.1.jar$BACKUP_SUFFIX" ]]; then
    RESTORE=yes
fi

msg "Папка игры: $GAME_DIR"
if [[ -n "$RESTORE" ]]; then
    msg "Обнаружена предыдущая установка перевода."
    if confirm_gui "Русский перевод уже установлен в эту копию игры.
Вернуть английский оригинал?"; then
        for t in "$APP_DIR/SemiSim-2.2.1.jar" "$APP_DIR/archive-tmp/SemiSim-2.2.1.jar"; do
            [[ -f "$t$BACKUP_SUFFIX" ]] && mv "$t$BACKUP_SUFFIX" "$t"
        done
        for n in README.html examples.html; do
            [[ -f "$APP_DIR/$n$BACKUP_SUFFIX" ]] && mv "$APP_DIR/$n$BACKUP_SUFFIX" "$APP_DIR/$n"
        done
        info_gui "Оригинал игры восстановлен. SemiSim снова на английском."
        exit 0
    fi
fi

if ! confirm_gui "Установить русский перевод в:
$GAME_DIR

Оригинал файлов будет сохранён рядом с расширением .orig"; then
    msg "Отменено — ничего не изменено."
    exit 0
fi

# бэкап и замена
count=0
for target in "$APP_DIR/SemiSim-2.2.1.jar" "$APP_DIR/archive-tmp/SemiSim-2.2.1.jar"; do
    [[ -f "$target" ]] || continue
    [[ -f "$target$BACKUP_SUFFIX" ]] || cp -p "$target" "$target$BACKUP_SUFFIX"
    cp "$RU_JAR" "$target" || fail "Не удалось заменить: $target"
    count=$((count + 1))
done

for name in README.html examples.html; do
    [[ -f "$HERE/help/$name" ]] || continue
    [[ -f "$APP_DIR/$name$BACKUP_SUFFIX" ]] || cp -p "$APP_DIR/$name" "$APP_DIR/$name$BACKUP_SUFFIX" 2>/dev/null
    cp "$HERE/help/$name" "$APP_DIR/$name"
done

[[ "$count" -gt 0 ]] || fail "Ни один файл игры не найден, ничего не изменено."

info_gui "Готово. Заменено файлов: $count

Теперь запускайте SemiSim из Steam — интерфейс будет на русском.

Если Steam вернул оригинал при проверке целостности,
запустите этот установщик заново.

Вернуть английский: запустите установщик ещё раз и согласитесь
на восстановление."

msg "Установлено: заменено файлов $count"
exit 0
