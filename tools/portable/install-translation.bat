@echo off
rem Russian translation installer for SemiSim, Windows, no exe needed.
rem Copies the translation next to the game and puts it first on the classpath.
rem No game file is replaced: SemiSim-2.2.1.jar stays original.
rem Double-click to run. If the game is not found, drag its folder onto this file.
chcp 1251 >nul
setlocal EnableDelayedExpansion

set "SELF=%~dp0"
set "MARKER=lib\app\SemiSim.cfg"
set "GAME=%~1"

if not defined GAME (
  for %%D in (
    "%ProgramFiles(x86)%\Steam\steamapps\common\SemiSim"
    "%ProgramFiles%\Steam\steamapps\common\SemiSim"
    "%ProgramW6432%\Steam\steamapps\common\SemiSim"
    "C:\Program Files (x86)\Steam\steamapps\common\SemiSim"
    "C:\Program Files\Steam\steamapps\common\SemiSim"
    "D:\Steam\steamapps\common\SemiSim"
    "D:\Games\Steam\steamapps\common\SemiSim"
    "E:\Steam\steamapps\common\SemiSim"
    "E:\Games\Steam\steamapps\common\SemiSim"
    "F:\Steam\steamapps\common\SemiSim"
  ) do (
    if exist "%%~D\%MARKER%" if not defined GAME set "GAME=%%~D"
  )
)

if not defined GAME (
  echo.
  echo   Game folder not found.
  echo.
  echo   Either copy this whole folder into the SemiSim game folder and run
  echo   it again, or drag the game folder onto this file.
  echo.
  pause
  exit /b 1
)

echo.
echo   Game folder: %GAME%
echo.
echo   What will be copied:
echo     - ru-patch.jar (translation, 265 KB) next to SemiSim-2.2.1.jar
echo     - README.html and examples.html (Russian help pages)
echo   and one line will be added to SemiSim.cfg:
echo     app.classpath=$APPDIR/ru-patch.jar
echo.
echo   No game file is replaced. Original help pages are kept as .orig
echo.
set /p ANS="   Continue? (Y/N) "
if /i not "%ANS%"=="Y" (
  echo   Cancelled, nothing was changed.
  pause
  exit /b 0
)

set "APPDIR=%GAME%\lib\app"

rem 1. translation package
copy /y "%SELF%ru-patch.jar" "%APPDIR%\ru-patch.jar" >nul || goto :err

rem 2. Russian help pages, keeping a backup of the originals
for %%H in (README.html examples.html) do (
  if exist "%APPDIR%\%%H" if not exist "%APPDIR%\%%H.orig" (
    copy /y "%APPDIR%\%%H" "%APPDIR%\%%H.orig" >nul
  )
  copy /y "%SELF%%%H" "%APPDIR%\%%H" >nul || goto :err
)

rem 3. classpath: our translation has to load before the game's own.
rem It goes right after the [Application] header: a line placed before the
rem header would fall outside the section and the jpackage launcher would
rem not read it. Lines are filtered by substring substitution, not findstr,
rem because findstr's /v behaves differently in different cmd hosts (Wine
rem ignores it outright) and the old line would be left in the file twice.
set "CFG=%APPDIR%\SemiSim.cfg"
if not exist "%CFG%" goto :err

set "TMP=%CFG%.ru-tmp"
if exist "%TMP%" del "%TMP%"
> "%TMP%" echo [Application]
>> "%TMP%" echo app.classpath=$APPDIR/ru-patch.jar
for /f "usebackq delims=" %%L in ("%CFG%") do call :copyline "%%L"
if not exist "%TMP%" goto :err
move /y "%TMP%" "%CFG%" >nul
if errorlevel 1 goto :err

echo.
echo   Done. The translation is active.
echo.
echo   Start the game through Steam as usual.
echo   To go back to English: delete the ru-patch.jar line from SemiSim.cfg
echo   and delete the file ru-patch.jar
echo.
pause
exit /b 0

:copyline
rem skip the section header and our own line: both are already written above,
rem otherwise a second run would duplicate them
set "LINE=%~1"
if /i "!LINE!"=="[Application]" goto :eof
if not "!LINE:ru-patch.jar=!"=="!LINE!" goto :eof
>> "%TMP%" echo !LINE!
goto :eof

:err
echo.
echo   Failed. Check that the game is not running and that
echo   lib\app\SemiSim.cfg exists in that folder.
echo.
pause
exit /b 1