# SemiSim — Russian translation

Russian interface for [SemiSim](https://store.steampowered.com/app/4864110/Brandons_Semiconductor_Simulator/)
(semiconductor physics simulator, version 2.2.1).

No game files here. The translation is applied as a separate package placed
next to your own copy of SemiSim — the game itself is never modified.

## What is translated

| Part | State |
|---|---|
| Menus, panels, buttons, tools | complete |
| Dialogs: settings, advanced settings, material editor, calculators | complete |
| Material names, view kinds, probes | complete |
| Error messages and confirmation questions | complete |
| Built-in help (manual and examples gallery) | complete |
| Cyrillic glyphs in the game's own bitmap font | 66 letters, added |
| Standard Swing dialog labels (Open, Cancel) | no, see Limitations |

Units and physics symbols (ρ, ϕ, Jₙ, [eV]) are deliberately left in Latin.

## Install in one click (Windows)

Download `setup.exe` (480 KB) and run it. It finds the SemiSim game folder on
its own and asks for confirmation. Nothing else to do: the translation and
the Russian help are already inside the file.

What it does:

* places `ru-patch.jar` next to the game — 265 KB, only the changed classes;
* adds one line to `SemiSim.cfg` so the translation loads first;
* replaces the help pages with the Russian ones, originals kept as `.orig`.

**No game file is modified at all.** `SemiSim-2.2.1.jar` stays original, so
Steam never restores it during its integrity check.

To go back to English, run `setup.exe` again and agree to the rollback.

`SemiSim-ru-setup.zip` has the full set: `setup.exe`, a 32-bit build and a
Linux build.

## Install without the installer: just copy files

`SemiSim-ru-portable.zip` (279 KB) is the same translation with no exe at all:

| File | What it is |
|---|---|
| `ru-patch.jar` | the translation, copy into `lib/app` next to the game's JAR |
| `README.html`, `examples.html` | Russian help pages |
| `install-translation.bat` | copies everything and fixes the config (Windows) |
| `install-translation.sh` | the same for Linux |
| `INSTALL-MANUAL.txt` | three ways to install, including plain manual copying |

The manual way in short: put `ru-patch.jar` into `lib/app` and add this line
at the top of the `app.classpath=` list in `SemiSim.cfg`:

```
app.classpath=$APPDIR/ru-patch.jar
```

## Why the game is never touched

Steam verifies the integrity of its own files and restores the original if you
replace the JAR. So the translation is put on the classpath instead: the JVM
takes the **first** class it finds, so a translation listed first overrides
the original, while `SemiSim-2.2.1.jar` stays untouched.

Verified live: with this classpath the main window is loaded from
`ru-patch.jar` and the dialogs read "Settings", "Material editor",
"Advanced settings".

## Run it manually (no installer)

Needs **JDK 25** — exactly 25, not 21: the JavaFX inside the game is built for
class file version 68, and older JVMs fail with `UnsupportedClassVersionError`.

```bash
git clone https://github.com/NeiP4n/SemiSim-ru
cd SemiSim-ru
bash tools/build.sh
```

The script finds the game's JAR by itself. If it does not, point it there:

```bash
SEMISIM_GAME_JAR=/path/to/SemiSim/lib/app/SemiSim-2.2.1.jar bash tools/build.sh
```

Then start the game with the translation:

```bash
./SemiSim-ru.sh
```

## Build from source

The translation is rebuilt from your own copy of the game: the dictionary
lives in the repository, the tool rewrites string constants straight in the
bytecode.

```bash
git clone https://github.com/NeiP4n/SemiSim-ru
cd SemiSim-ru
bash tools/build.sh          # checks + Russian JAR + translation package
bash tools/build_all.sh      # installer with the translation inside + portable archive
```

`build_dist.sh` and `build_portable.sh` verify their own output with
`tools/check_installer.py` and `tools/check_portable.py`: they make sure the
archives contain the translation only, not a single game file. Both checks can
also be told to fail — a check that never fails checks nothing.

## Dark theme

The game already has one; this translation did not add it. Go to
**File → Settings → UI theme → FlatLaf Dark → Apply**. Available: Metal,
Nimbus, CDE/Motif, GTK+, FlatLaf Light, FlatLaf Dark, Solarized Light,
Material Darker (Material) and High Contrast. The choice is saved in
`preferences.json` and survives a restart.

## How it works

The interface text is baked into the bytecode as string constants. The tools
rewrite those constants directly in the `.class` files, recomputing lengths,
and repackage the JAR. The game is not obfuscated, so reading and replacing is
reliable.

The main danger is strings that look like ordinary text but are actually keys.
The first version of the patch failed exactly there: translating `East` broke
`BorderLayout` (`cannot add to layout: unknown constraint: Восток`). Never
translated:

* save and settings keys (`theme`, `imgsize`, `SEMI_N_TYPE`, `rho_n` and 125
  more) — the game looks them up by string comparison, translating breaks file
  reading;
* Swing API constants (`North`, `Center`, `SansSerif`, …) — passed to the API;
* `SI` — the value of the `units` key in `preferences.json`; the enum has no
  separate display name.

The checks in `tools/build.sh` prevent such a mistake: the dictionary is
verified against the classification, and the classification against an oracle
that is deliberately broken and must notice.

## Translation integrity check

```bash
bash tools/negative_control.sh
```

The script breaks data on temporary copies (marks a key as translatable,
corrupts the opcode table, feeds a JAR without translations) and requires every
check to notice. If an oracle catches nothing, it checks nothing, and its green
output is worthless.

## Limitations

* Standard Swing dialog labels (`Open`, `Cancel`, `Look In`) are still English:
  they come from Java's own resources, not from the game's files. Translating
  them needs separate work on the FlatLaf bundle.
* Version 2.2.1. A different version will probably still build, but the
  dictionary has to be checked: `tools/extract.py` shows which strings changed.
* Formulas in the help are rendered by MathJax from a CDN — they need internet.

## License and attribution

SemiSim belongs to its author Brandon Li. This repository contains only the
translation and the tooling; no game files are distributed.

---

## Attribution

The interface translation, the help pages and all of the tooling in this
repository were generated by the **OpenCode (Space Bunny Free)** model.

Physics, terminology and wording were reviewed by a human; the accuracy of the
terms is the translator's responsibility, not the model's.