/*
 * Установщик русского перевода SemiSim (Windows и Linux).
 *
 * Что делает: ищет папку установленной игры, спрашивает подтверждение,
 * сохраняет оригиналы рядом с расширением .orig и кладёт на их место русские
 * файлы. Повторный запуск возвращает оригинал.
 *
 * Собран без внешних зависимостей: только WinAPI в Windows и POSIX в Linux.
 * Русские файлы кладутся рядом с программой в папке payload.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <windows.h>
#include <wchar.h>
#include <direct.h>
#define PATH_SEP '\\'
#define IS_DIR(p)         ((p).attrib & FILE_ATTRIBUTE_DIRECTORY)
#define FILE_EXISTS(p)    ((p).dwFileAttributes != INVALID_FILE_ATTRIBUTES)
typedef struct { char path[1024]; unsigned long size; } Info;
#else
#include <dirent.h>
#include <unistd.h>
#include <limits.h>
#define PATH_SEP '/'
#endif

#define JAR_NAME      "SemiSim-2.2.1.jar"
#define CFG_NAME      "SemiSim.cfg"
#define PATCH_NAME    "ru-patch.jar"
#define MARKER        "lib/app/" JAR_NAME
#define HELP_NAMES    "README.html", "examples.html"
#define PAYLOAD_JAR   "payload/" PATCH_NAME
#define PAYLOAD_H1    "payload/README.html"
#define PAYLOAD_H2    "payload/examples.html"
#define BACKUP_EXT    ".orig"
#define MAX_HITS      16
#ifndef MAX_PATH
#define MAX_PATH      1024
#endif

static int is_directory(const char *path)
{
#ifdef _WIN32
    WIN32_FIND_DATAA fd;
    HANDLE h;
    char pattern[MAX_PATH];
    int result = 0;
    snprintf(pattern, sizeof pattern, "%s\\*", path);
    h = FindFirstFileA(pattern, &fd);
    if (h != INVALID_HANDLE_VALUE) {
        result = (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) ? 1 : 0;
        FindClose(h);
    }
    return result;
#else
    struct stat st;
    return (stat(path, &st) == 0 && S_ISDIR(st.st_mode)) ? 1 : 0;
#endif
}

static int file_exists(const char *path)
{
#ifdef _WIN32
    WIN32_FIND_DATAA fd;
    HANDLE h;
    h = FindFirstFileA(path, &fd);
    if (h == INVALID_HANDLE_VALUE)
        return 0;
    FindClose(h);
    return 1;
#else
    struct stat st;
    return stat(path, &st) == 0;
#endif
}

static void join(char *out, size_t n, const char *a, const char *b)
{
    snprintf(out, n, "%s%c%s", a, PATH_SEP, b);
}

/* Копирование файла: сначала во временный, потом переименование, чтобы
 * не оставить игру с обрезанным файлом, если копирование прервётся. */
static int copy_file(const char *from, const char *to)
{
    FILE *in, *out;
    char buffer[65536];
    size_t n;
    char tmp[MAX_PATH];

    snprintf(tmp, sizeof tmp, "%s.tmp", to);
    in = fopen(from, "rb");
    if (!in) {
        fprintf(stderr, "cannot read %s\n", from);
        return 0;
    }
    out = fopen(tmp, "wb");
    if (!out) {
        fclose(in);
        fprintf(stderr, "cannot write %s\n", tmp);
        return 0;
    }
    while ((n = fread(buffer, 1, sizeof buffer, in)) > 0) {
        if (fwrite(buffer, 1, n, out) != n) {
            fclose(in);
            fclose(out);
            remove(tmp);
            fprintf(stderr, "write error %s\n", tmp);
            return 0;
        }
    }
    fclose(in);
    if (fclose(out) != 0) {
        remove(tmp);
        return 0;
    }
    remove(to);
    if (rename(tmp, to) != 0) {
        remove(tmp);
        fprintf(stderr, "cannot replace %s\n", to);
        return 0;
    }
    return 1;
}

/* Полный путь к самой программе — из него читаем приклеенный перевод. */
static int self_path(char *out, size_t n)
{
#ifdef _WIN32
    DWORD written = GetModuleFileNameA(NULL, out, (DWORD) n);
    return written ? 1 : 0;
#else
    ssize_t len = readlink("/proc/self/exe", out, n - 1);
    if (len <= 0)
        return 0;
    out[len] = '\0';
    return 1;
#endif
}

static int self_dir(char *out, size_t n)
{
    char *slash;
    if (!self_path(out, n))
        return 0;
    slash = strrchr(out, '/');
#ifdef _WIN32
    if (!slash)
        slash = strrchr(out, '\\');
    if (slash)
        *slash = '\0';
#else
    if (slash)
        *slash = '\0';
#endif
    return 1;
}

/* Дописать наш classpath ПЕРЕД игровым: JVM берёт первый найденный класс,
 * поэтому перевод перекрывает оригинал, а файлы игры остаются нетронутыми. */
static int add_classpath(const char *game)
{
    char cfg[MAX_PATH], line[512], tmp[MAX_PATH];
    FILE *in, *out;
    int written = 0;

    snprintf(cfg, sizeof cfg, "%s/lib/app/" CFG_NAME, game);
    snprintf(tmp, sizeof tmp, "%s.tmp", cfg);
    in = fopen(cfg, "r");
    if (!in)
        return 0;
    out = fopen(tmp, "w");
    if (!out) {
        fclose(in);
        return 0;
    }
    while (fgets(line, sizeof line, in)) {
        if (strstr(line, PATCH_NAME))
            continue;                     /* не плодим дубли */
        if (!written && strncmp(line, "app.classpath=", 14) == 0) {
            /* наш classpath должен идти раньше игрового; вставляем один раз,
             * иначе строка продублируется по числу classpath в cfg */
            fprintf(out, "app.classpath=$APPDIR/%s\n", PATCH_NAME);
            written = 1;
        }
        fputs(line, out);
    }
    fclose(in);
    if (fclose(out) != 0) {
        remove(tmp);
        return 0;
    }
    if (written) {
        remove(cfg);
        if (rename(tmp, cfg) != 0) {
            remove(tmp);
            return 0;
        }
    } else {
        remove(tmp);
    }
    return written;
}

/* Убрать наш classpath — откат. */
static void remove_classpath(const char *game)
{
    char cfg[MAX_PATH], line[512], tmp[MAX_PATH];
    FILE *in, *out;
    snprintf(cfg, sizeof cfg, "%s/lib/app/" CFG_NAME, game);
    snprintf(tmp, sizeof tmp, "%s.tmp", cfg);
    in = fopen(cfg, "r");
    if (!in)
        return;
    out = fopen(tmp, "w");
    if (!out) {
        fclose(in);
        return;
    }
    while (fgets(line, sizeof line, in)) {
        if (strstr(line, PATCH_NAME))
            continue;
        fputs(line, out);
    }
    fclose(in);
    fclose(out);
    remove(cfg);
    rename(tmp, cfg);
}

/* Обход каталогов вглубь: ищем папку, где лежит lib/app/<jar> */
static int scan(const char *dir, int depth, char hits[][MAX_PATH], int *count)
{
    char full[MAX_PATH];
    char probe[MAX_PATH];

    if (depth < 0 || *count >= MAX_HITS)
        return 0;

    snprintf(probe, sizeof probe, "%s/%s", dir, MARKER);
    if (file_exists(probe)) {
        snprintf(hits[*count], MAX_PATH, "%s", dir);
        (*count)++;
        return 0;
    }
    if (depth == 0)
        return 0;

#ifdef _WIN32
    {
        WIN32_FIND_DATAA fd;
        HANDLE h;
        snprintf(full, sizeof full, "%s\\*", dir);
        h = FindFirstFileA(full, &fd);
        if (h == INVALID_HANDLE_VALUE)
            return 0;
        do {
            if (strcmp(fd.cFileName, ".") == 0 || strcmp(fd.cFileName, "..") == 0)
                continue;
            if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
                continue;
            join(full, sizeof full, dir, fd.cFileName);
            scan(full, depth - 1, hits, count);
        } while (FindNextFileA(h, &fd) && *count < MAX_HITS);
        FindClose(h);
    }
#else
    {
        DIR *d = opendir(dir);
        struct dirent *entry;
        if (!d)
            return 0;
        while ((entry = readdir(d)) != NULL && *count < MAX_HITS) {
            if (entry->d_name[0] == '.')
                continue;
            join(full, sizeof full, dir, entry->d_name);
            if (is_directory(full))
                scan(full, depth - 1, hits, count);
        }
        closedir(d);
    }
#endif
    return 0;
}

static void notify(const char *text);
static int confirm(const char *text);

/* Встроенные в установщик русские файлы.
 *
 * К концу собственного .exe приклеен блок:
 *   "SEMISIMPAYL" (11 байт) | int32 count | записи
 *   запись: char name[64] | int32 size | байты файла
 * Распаковывать ничего не нужно: файлы копируются как есть, поэтому
 * разбирать zip не требуется. */
#define PAYLOAD_MAGIC  "SEMISIMPAYL"
#define PAYLOAD_MAGIC_LEN 11
#define PAYLOAD_TAIL   "SEMISIMEND"
#define PAYLOAD_TAIL_LEN 10
#define ENTRY_NAME_LEN 64

static char temp_payload[3][MAX_PATH];

static void cleanup_temp(void)
{
    int i;
    for (i = 0; i < 3; i++) {
        if (temp_payload[i][0]) {
            remove(temp_payload[i]);
            temp_payload[i][0] = 0;
        }
    }
}

/* Извлечь встроенные файлы во временную папку игры.
 * Возвращает число извлечённых файлов или -1 при ошибке. */
static int extract_payload(const char *base)
{
    char self[MAX_PATH], chunk[MAX_PATH + 40];
    FILE *in, *entry;
    char magic[PAYLOAD_MAGIC_LEN];
    int count = 0, taken = 0, i;

    if (!self_path(self, sizeof self))
        return -1;
    in = fopen(self, "rb");
    if (!in)
        return -1;
    /* в хвосте файла: завершающий маркер и смещение блока */
    {
        char tail[PAYLOAD_TAIL_LEN];
        long long offset;
        if (fseek(in, -(long)(PAYLOAD_TAIL_LEN + 8), SEEK_END) != 0 ||
            fread(tail, 1, PAYLOAD_TAIL_LEN, in) != PAYLOAD_TAIL_LEN ||
            memcmp(tail, PAYLOAD_TAIL, PAYLOAD_TAIL_LEN) != 0) {
            fclose(in);
            return -1;   /* установщик собран без встроенных файлов */
        }
        if (fread(&offset, sizeof offset, 1, in) != 1 || offset <= 0) {
            fclose(in);
            return -1;
        }
        if (fseek(in, (long)offset, SEEK_SET) != 0) {
            fclose(in);
            return -1;
        }
    }
    if (fread(magic, 1, PAYLOAD_MAGIC_LEN, in) != PAYLOAD_MAGIC_LEN ||
        memcmp(magic, PAYLOAD_MAGIC, PAYLOAD_MAGIC_LEN) != 0) {
        fclose(in);
        return -1;
    }
    if (fread(&count, sizeof count, 1, in) != 1 || count <= 0 || count > 16) {
        fclose(in);
        return -1;
    }
    for (i = 0; i < count; i++) {
        char name[ENTRY_NAME_LEN];
        int size;
        if (fread(name, 1, ENTRY_NAME_LEN, in) != ENTRY_NAME_LEN) break;
        name[ENTRY_NAME_LEN - 1] = 0;
        if (fread(&size, sizeof size, 1, in) != 1 || size <= 0) break;
        snprintf(chunk, sizeof chunk, "%s.tmp_payload", base);
        entry = fopen(chunk, "wb");
        if (!entry) break;
        {
            char buf[65536];
            int left = size;
            while (left > 0) {
                size_t want = (size_t)(left < (int)sizeof buf ? left : (int)sizeof buf);
                size_t got = fread(buf, 1, want, in);
                if (got == 0) break;
                fwrite(buf, 1, got, entry);
                left -= (int)got;
            }
        }
        fclose(entry);
        if (taken < 3) {
            snprintf(temp_payload[taken], MAX_PATH, "%s/.semisim_payload_%d_%s",
                     base, taken, name);
            if (rename(chunk, temp_payload[taken]) != 0)
                remove(chunk);
            else
                taken++;
        } else {
            remove(chunk);
        }
    }
    fclose(in);
    return taken;
}

/* Перевод UTF-8 в UTF-16 для WinAPI.
 *
 * MessageBoxA ждёт ANSI в кодировке системы (у русской Windows это cp1251),
 * а исходник у нас в UTF-8: русский текст превратился бы в мусор. Поэтому
 * весь текст идёт только через MessageBoxW. */
#ifdef _WIN32
static void to_wide(const char *src, wchar_t *dst, size_t n)
{
    int written = MultiByteToWideChar(CP_UTF8, 0, src, -1, dst, (int) n);
    if (written <= 0)
        wcscpy_s(dst, n, L"?");
}
#endif

static int confirm(const char *text)
{
#ifdef _WIN32
    wchar_t wide[2048], title[128];
    to_wide(text, wide, 2048);
    to_wide("Install the SemiSim Russian translation", title, 128);
    return MessageBoxW(NULL, wide, title, MB_OKCANCEL | MB_ICONQUESTION) == IDOK;
#else
    char answer[8];
    printf("%s [y/N] ", text);
    fflush(stdout);
    if (!fgets(answer, sizeof answer, stdin))
        return 0;
    return answer[0] == 'y' || answer[0] == 'Y' || answer[0] == '\xd1';
#endif
}

static void notify(const char *text)
{
#ifdef _WIN32
    wchar_t wide[2048], title[128];
    to_wide(text, wide, 2048);
    to_wide("SemiSim Russian translation", title, 128);
    MessageBoxW(NULL, wide, title, MB_OK | MB_ICONINFORMATION);
#else
    printf("%s\n", text);
    (void) getchar();
#endif
}

static void fail(const char *text)
{
#ifdef _WIN32
    wchar_t wide[2048], title[128];
    to_wide(text, wide, 2048);
    to_wide("Failed", title, 128);
    MessageBoxW(NULL, wide, title, MB_OK | MB_ICONERROR);
#else
    fprintf(stderr, "%s\n", text);
#endif
}

int main(int argc, char **argv)
{
    char base[MAX_PATH], hits[MAX_HITS][MAX_PATH];
    char src[MAX_PATH], dst[MAX_PATH], probe[MAX_PATH];
    char text[2048];
    const char *help_names[2] = { HELP_NAMES };
    const char *embedded_help1 = NULL, *embedded_help2 = NULL;
    int embedded = 0;
    int count = 0, replaced = 0, i, restored = 0;
    const char *game;

#ifdef _WIN32
    SetConsoleOutputCP(65001);
#endif

    if (!self_dir(base, sizeof base)) {
        fprintf(stderr, "cannot locate the program folder\n");
        return 1;
    }
    embedded = extract_payload(base);
    if (embedded > 0) {
        /* запись 0 — пакет перевода, 1 и 2 — русская справка */
        snprintf(src, sizeof src, "%s", temp_payload[0]);
        embedded_help1 = (embedded > 1) ? temp_payload[1] : NULL;
        embedded_help2 = (embedded > 2) ? temp_payload[2] : NULL;
    } else {
        src[0] = 0;
    }

    if (src[0] == 0) {
        join(src, sizeof src, base, PAYLOAD_JAR);
        char msg[1024];
        snprintf(msg, sizeof msg,
                 "No translation package next to the installer.\n\n"
                 "Expected:\n  payload\\" PATCH_NAME "\n\n"
                 "The installer only copies ready files, so it needs the\n"
                 "translation package to do anything.\n\n"
                 "In the project folder run:\n"
                 "  bash tools/build_dist.sh\n\n"
                 "then run setup.exe from the dist folder.");
        notify(msg);
        return 1;
    }

    /* Явно указанная папка важнее поиска: так скрипт можно запустить с аргументом */
    if (argc > 1) {
        join(probe, sizeof probe, argv[1], MARKER);
        if (!file_exists(probe)) {
            fprintf(stderr, "no file %s in %s\n", argv[1], MARKER);
            return 1;
        }
        snprintf(hits[0], MAX_PATH, "%s", argv[1]);
        count = 1;
    } else {
        scan(base, 3, hits, &count);
        if (count == 0) {
            char root[MAX_PATH];
            const char *home = getenv("HOME");
#ifdef _WIN32
            home = getenv("USERPROFILE");
#endif
            if (home) {
                snprintf(root, sizeof root, "%s", home);
                scan(root, 4, hits, &count);
            }
        }
    }

    if (count == 0) {
        fprintf(stderr, "SemiSim not found.\n"
                        "Copy this folder into the game folder and run the installer again.\n");
        return 1;
    }
    if (count > 1)
        fprintf(stderr, "game copies found: %d, using the first.\n", count);

    game = hits[0];
    fprintf(stderr, "Game folder: %s\n", game);

    /* Повторный запуск: бэкап есть — это откат */
    join(probe, sizeof probe, game, "lib/app/" PATCH_NAME);
    if (file_exists(probe)) {
        snprintf(text, sizeof text,
                 "The Russian translation is already installed in this game copy.\n"
                 "Restore the English original?\n\n%s", game);
        if (confirm(text)) {
            char patch[MAX_PATH];
            remove_classpath(game);
            snprintf(patch, sizeof patch, "%s/lib/app/" PATCH_NAME, game);
            if (file_exists(patch))
                remove(patch);
            notify("The Russian translation is disabled. The game is in English again.\n"
                   "No game file was changed.");
            return 0;
        }
        fprintf(stderr, "Cancelled - nothing was changed.\n");
        return 0;
    }

    snprintf(text, sizeof text,
             "Install the Russian translation into:\n%s\n\n"
             "No game file is replaced: " PATCH_NAME " will appear next to it,\n"
             "listed first on the classpath.\n"
             "The original help pages are kept with the .orig extension", game);
    if (!confirm(text)) {
        fprintf(stderr, "Cancelled - nothing was changed.\n");
        return 0;
    }

    /* Кладём рядом с игрой наш пакет с переводом и прописываем его в classpath.
     * Файлы игры при этом не трогаем вообще. */
    {
        char patch[MAX_PATH];
        snprintf(patch, sizeof patch, "%s/lib/app/" PATCH_NAME, game);
        if (!copy_file(src, patch)) {
            notify("Could not write the translation file.");
            return 1;
        }
        replaced++;
        if (!add_classpath(game)) {
            notify("Could not register the translation in " CFG_NAME "\n"
                   "Copy it by hand: lib\\" PATCH_NAME "\n"
                   "to the top of the app.classpath= list in " CFG_NAME);
            return 1;
        }
    }

    /* Русская справка кладётся рядом с игрой */
    for (i = 0; i < 2; i++) {
        char payload[MAX_PATH], target[MAX_PATH], backup[MAX_PATH];
        if (embedded_help1 && embedded_help2) {
            snprintf(payload, sizeof payload, "%s", i == 0 ? embedded_help1 : embedded_help2);
        } else {
            join(payload, sizeof payload, base, i == 0 ? PAYLOAD_H1 : PAYLOAD_H2);
        }
        if (!file_exists(payload))
            continue;
        snprintf(target, sizeof target, "%s/lib/app/%s", game, help_names[i]);
        snprintf(backup, sizeof backup, "%s" BACKUP_EXT, target);
        if (file_exists(target) && !file_exists(backup))
            copy_file(target, backup);
        copy_file(payload, target);
    }
    cleanup_temp();

    if (replaced == 0) {
        fprintf(stderr, "No game file was replaced.\n");
        return 1;
    }

    cleanup_temp();

    snprintf(text, sizeof text,
             "Done.\n\n"
             "Start SemiSim through Steam as usual - the interface will be in Russian.\n\n"
             "No game file was changed.\n\n"
             "To go back to English: run this installer again.", replaced);
    notify(text);
    return 0;
}
