@echo off
rem Установка русского перевода SemiSim без установщика.
rem Копирует пакет перевода в папку игры и прописывает его первым в classpath.
rem Файлы игры не заменяются: SemiSim-2.2.1.jar остаётся оригинальным.
rem Запускается двойным кликом. Если игру не нашли — перетащите её папку на этот файл.
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
  echo   Папка игры не найдена.
  echo.
  echo   Сделайте так: скопируйте эту папку в папку игры SemiSim
  echo   и запустите файл оттуда. Либо перетащите папку игры на этот файл.
  echo.
  pause
  exit /b 1
)

echo.
echo   Папка игры: %GAME%
echo.
echo   Будет скопировано:
echo     - ru-patch.jar (перевод, 265 КБ) рядом с SemiSim-2.2.1.jar
echo     - README.html и examples.html (русская справка)
echo   И в SemiSim.cfg появится одна строка: app.classpath=$APPDIR/ru-patch.jar
echo.
echo   Файлы игры не заменяются. Оригиналы справки сохранятся как .orig
echo.
set /p ANS="   Продолжить? (Y/N) "
if /i not "%ANS%"=="Y" (
  echo   Отменено, ничего не изменено.
  pause
  exit /b 0
)

set "APPDIR=%GAME%\lib\app"

rem 1. пакет перевода
copy /y "%SELF%ru-patch.jar" "%APPDIR%\ru-patch.jar" >nul || goto :err

rem 2. русская справка, с бэкапом оригинала
for %%H in (README.html examples.html) do (
  if exist "%APPDIR%\%%H" if not exist "%APPDIR%\%%H.orig" (
    copy /y "%APPDIR%\%%H" "%APPDIR%\%%H.orig" >nul
  )
  copy /y "%SELF%%%H" "%APPDIR%\%%H" >nul || goto :err
)

rem 3. classpath: наш перевод должен грузиться раньше игрового.
rem Наша строка идёт первой в файле — значит она первая и в classpath.
rem Порядок строк задаёт порядок загрузки классов, а не сам факт строки.
set "CFG=%APPDIR%\SemiSim.cfg"
if not exist "%CFG%" goto :err

set "TMP=%CFG%.ru-tmp"
if exist "%TMP%" del "%TMP%"
rem наш перевод идёт сразу после заголовка секции [Application]: строка
rem до заголовка оказалась бы вне секции и jpackage-лаунчер её не прочтёт
> "%TMP%" echo [Application]
>> "%TMP%" echo app.classpath=$APPDIR/ru-patch.jar
rem Фильтруем построчно подстановкой подстроки, а не findstr: у findstr
rem ключ /v с литеральным поиском ведёт себя по-разному в разных cmd
rem (в Wine он вовсе игнорируется), и старая строка перевода оставалась бы
rem в файле дважды. Проверено: подстановка работает одинаково везде.
for /f "usebackq delims=" %%L in ("%CFG%") do call :copyline "%%L"
if not exist "%TMP%" goto :err
move /y "%TMP%" "%CFG%" >nul
if errorlevel 1 goto :err

echo.
echo   Готово. Перевод включён.
echo.
echo   Запустите игру как обычно, через Steam.
echo   Вернуть английский: удалите из SemiSim.cfg строку
echo   app.classpath=...ru-patch.jar и удалите файл ru-patch.jar
echo.
pause
exit /b 0

:copyline
rem заголовок секции и строку с нашим переводом пропускаем: они уже
rem записаны выше, иначе при повторном запуске задвоятся
set "LINE=%~1"
if /i "!LINE!"=="[Application]" goto :eof
if not "!LINE:ru-patch.jar=!"=="!LINE!" goto :eof
>> "%TMP%" echo !LINE!
goto :eof

:err
echo.
echo   Не получилось. Проверьте, что папка игры не занята игрой,
echo   и что в ней есть файл lib\app\SemiSim.cfg
echo.
pause
exit /b 1