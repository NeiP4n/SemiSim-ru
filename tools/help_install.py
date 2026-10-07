"""Установка русской справки рядом с JAR.

Справка НЕ лежит внутри архива: файлы README.html и examples.html игра ищет
по имени в своей рабочей папке (рядом с JAR), а не как ресурс в classpath.
Поэтому в JAR их добавлять бессмысленно — нужно положить файлы в out/.

Проверено чтением байткода electrodynamics.Controls: строки 'README.html' и
'examples.html' используются как имена файлов, а в архиве игры их нет.
"""

import argparse
import json
import os
import shutil
import sys

HELP_FILES = ("README.html", "examples.html")


def install(help_dir, target_dir, report_path=None):
    """Скопировать переведённую справку в папку запуска игры."""
    missing = [n for n in HELP_FILES if not os.path.isfile(os.path.join(help_dir, n))]
    if missing:
        print(f"нет файлов справки: {missing}", file=sys.stderr)
        return None
    os.makedirs(target_dir, exist_ok=True)
    installed = {}
    for name in HELP_FILES:
        src = os.path.join(help_dir, name)
        dst = os.path.join(target_dir, name)
        shutil.copyfile(src, dst)
        installed[name] = os.path.getsize(dst)
    report = {"installed": installed, "target_dir": target_dir}
    if report_path:
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--help-dir", required=True, help="папка с переведённой справкой")
    ap.add_argument("--target-dir", required=True, help="куда положить (папка с JAR)")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    report = install(args.help_dir, args.target_dir, args.report)
    if report is None:
        return 1
    print(f"справка установлена в {report['target_dir']}")
    for name, size in report["installed"].items():
        print(f"  {name}: {size} байт")
    return 0


if __name__ == "__main__":
    sys.exit(main())
