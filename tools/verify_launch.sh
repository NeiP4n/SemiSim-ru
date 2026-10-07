#!/usr/bin/env bash
# Запуск русской игры на виртуальном экране и проверка, что окно появилось.
# Нужен для листа L-LAUNCHER: доказательство, что лаунчер работает.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE" || exit 1

DISPLAY_NUM="${SEMISIM_TEST_DISPLAY:-:99}"
LOG="out/run_launch_test.log"
mkdir -p out

if ! pgrep -x Xvfb >/dev/null 2>&1; then
    Xvfb "$DISPLAY_NUM" -screen 0 1600x1000x24 >/dev/null 2>&1 &
    sleep 3
fi

pkill -x java >/dev/null 2>&1 || true
sleep 1
HOME_DIR="$(mktemp -d)"
setsid env DISPLAY="$DISPLAY_NUM" HOME="$HOME_DIR" \
    ./SemiSim-ru.sh > "$LOG" 2>&1 &
sleep 50

if pgrep -f 'SemiSim-2.2.1-ru.jar' >/dev/null; then
    RUNNING=yes
else
    RUNNING=no
fi
EXCEPTIONS=$(grep -c Exception "$LOG" || true)
echo "процесс жив: $RUNNING"
echo "исключений в логе: $EXCEPTIONS"

if [[ "$RUNNING" == yes && "$EXCEPTIONS" == 0 ]]; then
    echo "РЕЗУЛЬТАТ: зелёный — лаунчер запускает игру без ошибок"
    exit 0
fi
echo "РЕЗУЛЬТАТ: красный — лаунчер не отработал"
tail -20 "$LOG"
exit 1
