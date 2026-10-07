"""Оракул классификации строк: ключи не должны попадать в переводимые.

Проверяет две стороны решения одновременно:
  1. известные ключи сохранений и настроек обязаны быть запрещены;
  2. известные надписи меню обязаны быть видимыми.

Это осознанно «список ожиданий», а не проверка самого кода классификатора:
именно он защищает от тихой ошибки, когда правило начнёт считать ключ
переводимым и патч сломает чтение сохранений.

Запуск с флагом --self-test ломает правило намеренно и требует, чтобы
проверка это заметила.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "..", "out", "strings.json")

# Ключи, которые нельзя переводить ни при каких условиях.
# Источники: имена полей в .semisim и preferences.json; ключи, по которым
# AdvancedOptions и Preferences сравнивают строки; имена констант перечислений,
# участвующие в сериализации материалов.
MUST_FORBID = [
    # ключи preferences.json
    "theme",
    "windowstate",
    "imgsize",
    "imgsize_x",
    "imgsize_y",
    "units",
    "fps",
    "fps_sim",
    "fontsize",
    "undosize",
    "matname",
    "voltage",
    "potential",
    "undotrackssettings",
    "preferences",
    "version",
    # ключи сохранений .semisim
    "materials",
    "materialmap",
    "all_probes",
    "voltageprobes",
    "currentprobes",
    "chargeprobes",
    "fluxprobes",
    "last_material_id",
    "description",
    "advsettings",
    "header",
    "data",
    "nx",
    "ny",
    "ds",
    "time",
    "phase",
    "resolution",
    "width",
    "rho_n",
    "rho_p",
    "rho_c",
    "rho_back",
    "rho_free",
    "jx_n",
    "jy_n",
    "jx_p",
    "jy_p",
    "jx_c",
    "jy_c",
    "ex",
    "ey",
    "hz",
    "scalarmode",
    "vectormode",
    "scalarview",
    "vectorview",
    "gui_bc",
    "gui_view",
    "gui_view_vec",
    "gui_view_vec_mode",
    # ключи расширенных настроек материала
    "Eg_metal",
    "W_metal_high",
    "W_metal_low",
    "k_rad_metal",
    "mu_electron_metal",
    "mu_hole_metal",
    "eps_r_metal",
    "dielectric_eps_r",
    "ferromagnet_mu_r",
    "staticcharge_density",
    "currentsource_mobility",
    "max_EMF",
    "max_current",
    "default_AC_freq",
    "switch_open_mobility",
    "a_factor_n",
    "a_factor_p",
    "eps_r_semi",
    "modified_names",
    "Eg_semi",
    "k_rad_semi",
    "k_SRH_n_semi",
    "k_SRH_p_semi",
    "k_aug_n_semi",
    "k_aug_p_semi",
    "v_sat_n",
    "v_sat_p",
    "dopant_smoothing_distance",
    "junction_size",
    # ключи контролов: передаются в setActionCommand
    "gui_material",
    "show_probearrows",
    # имена констант перечислений: участвуют в сериализации и Enum.valueOf
    "SEMI_N_TYPE",
    "SEMI_P_TYPE",
    "SEMI_HEAVY_N_TYPE",
    "SEMI_LIGHT_P_TYPE",
    "METAL",
    "METAL_HIGH_C",
    "METAL_LOW_W",
    "DIELECTRIC",
    "FERROMAGNET",
    "ABSORBER",
    "VACUUM",
    "POS_CHARGE",
    "NEG_CHARGE",
    "SEMICONDUCTING",
    "AVERAGE_POTENTIAL",
    "DELETEPROBE",
    "SCALARPLOT",
    "PROBEPLOT",
    "XYPLOT",
    "B_FIELD",
    "POTENTIAL",
    "RECOMB_SRH",
    "RECOMB_RAD",
    "RECOMB_AUGER",
    "TOTAL_CURRENT",
    "ELECTRIC_POTENTIAL",
    "MAGNETIC_FLUX_DENSITY",
    # имена файлов: игра открывает их по имени
    "preferences.json",
    "probedata.txt",
    "error_log.txt",
    "workshop_item.semisim",
    # значения, передаваемые в API Swing: перевод ломает программу.
    # Проверено запуском: перевод "East" роняет игру с
    # IllegalArgumentException: cannot add to layout: unknown constraint
    "North",
    "South",
    "East",
    "West",
    "Center",
    "none",
    "normal",
    # логические имена шрифтов java.awt.Font
    "SansSerif",
    "Monospaced",
    # значение ключа "units" в preferences.json: у перечисления Units нет
    # отдельного отображаемого имени, перевод ломает чтение настроек
    "SI",
]

# Надписи, которые пользователь видит и которые обязаны быть переводимыми.
MUST_VISIBLE = [
    # меню верхнего уровня
    "File",
    "Edit",
    "Tools",
    "View",
    "Graphics",
    "Examples",
    "Help",
    # пункты меню
    "Save",
    "Save as...",
    "Open file...",
    "Load",
    "Exit",
    "Undo",
    "Redo",
    "Copy",
    "Cut",
    "Paste",
    "Select all",
    "Deselect all",
    "About...",
    "Preferences",
    "New simulation...",
    "Edit description...",
    "Report a bug...",
    "Open manual",
    "Open workshop item",
    "Browse all examples",
    "Export material(s)",
    "Import material(s)",
    # панель управления
    "Reset fields",
    "Timestep: ",
    "Sim steps/frame: ",
    "Scalar brightness",
    "Vector field brightness",
    "Show charge carriers",
    "Description of simulation",
    # инструменты и материалы
    "Interact",
    "Zoom",
    "Pan",
    "Draw",
    "Eraser",
    "Flashlight",
    "Ruler",
    "Select and Move",
    "Voltage source",
    "Current source",
    "AC voltage source",
    "Metal",
    "Semiconductor",
    "Dielectric",
    "Ferromagnet",
    "Absorber",
    "Vacuum",
    "Insulator",
    "Conductor",
    "Switch",
    "Decoration",
    "Ground",
    # окна и сообщения
    "Error!",
    "Message",
    "Cancel",
    "Close",
    "Yes",
    "No",
    "OK",
    "There are unsaved changes. Do you still wish to quit?",
    "Error: Numerical overflow detected. Please reset simulation.",
    # виды отображения: в игре символ входит в название, поэтому строка
    # начинается с "View E:", а не с "View:"
    "View E: Electric field",
    "View H field",
    "View V: Voltage",
    "View J: Total current magnitude",
    "View nₙ: Electron density",
]


def load_report(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check(report):
    """Вернуть (ошибки, сводка). Ошибки — список строк с объяснением."""
    visible = set(report["visible"])
    forbidden = set(report["forbidden"])
    errors = []
    for key in MUST_FORBID:
        if key not in forbidden:
            where = "видимая" if key in visible else "отсутствует"
            errors.append(
                f"КЛЮЧ «{key}» помечен как {where} — перевод сломает сохранения"
            )
    for label in MUST_VISIBLE:
        if label not in visible:
            where = "запрещённая" if label in forbidden else "отсутствующая"
            errors.append(
                f"НАДПИСЬ «{label}» помечена как {where} — она останется без перевода"
            )
    summary = f"проверено ключей: {len(MUST_FORBID)}, надписей: {len(MUST_VISIBLE)}"
    return errors, summary


def main():
    # первый аргумент — путь к отчёту, если он не начинается с --
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = positional[0] if positional else REPORT
    if not os.path.exists(path):
        print(f"нет отчёта {path}: сначала tools/extract.py", file=sys.stderr)
        return 2
    report = load_report(path)
    if "--self-test" in sys.argv:
        # Намеренная порча: объявляем ключ переводимым и требуем, чтобы
        # проверка это заметила. Если ошибок нет — оракул негоден.
        report["visible"] = list(report["visible"]) + ["theme", "gui_material"]
        report["forbidden"] = [
            k for k in report["forbidden"] if k not in ("theme", "gui_material")
        ]
        errors, _ = check(report)
        if not errors:
            print("ОРАКУЛ НЕГОДЕН: сломанную классификацию не заметил")
            return 1
        print(f"ОРАКУЛ ГОДЕН: поймал {len(errors)} ошибок на испорченных данных")
        return 0

    errors, summary = check(report)
    print(summary)
    if errors:
        print(f"НАРУШЕНИЙ: {len(errors)}")
        for line in errors[:20]:
            print(f"  {line}")
        if len(errors) > 20:
            print(f"  ... ещё {len(errors) - 20}")
        return 1
    print("РЕЗУЛЬТАТ: зелёный — ключи и надписи размечены верно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
