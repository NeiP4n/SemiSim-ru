#!/usr/bin/env bash
# Собрать оба готовых набора раздачи:
#   dist/SemiSim-ru-setup.zip     — установщик setup.exe с переводом внутри
#   dist/SemiSim-ru-portable.zip  — файлы для копирования и скрипты установки
#
# Оба набора содержат только перевод: файлов игры в них нет, и оба это
# проверяют оракулами check_installer.py и check_portable.py.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

echo "== установщик =="
bash tools/build_dist.sh

echo
echo "== портативный набор =="
bash tools/build_portable.sh

echo
echo "оба набора собраны:"
ls -la dist/*.zip