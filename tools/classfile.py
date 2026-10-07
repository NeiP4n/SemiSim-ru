"""Чтение и перезапись пула констант .class без внешних зависимостей.

Модуль нужен для патча строк в готовом JAR игры: текст интерфейса лежит
в константах Utf8, а смена длины строки сдвигает весь хвост файла.

Индексы констант в байткоде не меняются (они ссылки на номера, а не на
смещения), поэтому достаточно пересобрать пул и пришить хвост как есть.
"""

import struct

MAGIC = b"\xca\xfe\xba\xbe"

# Занимает два слота в пуле — сдвигает нумерацию следующих записей.
WIDE_TAGS = {5, 6}  # Long, Double

FIXED_SIZE = {3: 4, 4: 4, 9: 4, 10: 4, 11: 4, 12: 4, 17: 4, 18: 4, 15: 3}
TAG_SIZE = {
    7: 2,
    8: 2,
    16: 2,
    19: 2,
    20: 2,  # Class, String, MethodType, Module, Package
    5: 8,
    6: 8,  # Long, Double
}


def to_mutf8(text):
    """Кодирование в модифицированный UTF-8, как требует формат .class.

    Отличия от обычного UTF-8: NUL записывается как C0 80, а символы вне
    BMP — суррогатной парой по три байта каждый.
    """
    out = bytearray()
    for ch in text:
        cp = ord(ch)
        if cp == 0:
            out += b"\xc0\x80"
        elif cp < 0x80:
            out.append(cp)
        elif cp < 0x800:
            out.append(0xC0 | (cp >> 6))
            out.append(0x80 | (cp & 0x3F))
        elif cp < 0x10000:
            out.append(0xE0 | (cp >> 12))
            out.append(0x80 | ((cp >> 6) & 0x3F))
            out.append(0x80 | (cp & 0x3F))
        else:
            rest = cp - 0x10000
            for unit in (0xD800 + (rest >> 10), 0xDC00 + (rest & 0x3FF)):
                out.append(0xE0 | (unit >> 12))
                out.append(0x80 | ((unit >> 6) & 0x3F))
                out.append(0x80 | (unit & 0x3F))
    return bytes(out)


def from_mutf8(raw):
    """Обратное преобразование; нераспознанные байты не роняют разбор."""
    fixed = raw.replace(b"\xc0\x80", b"\x00")
    return fixed.decode("utf-8", errors="replace")


class ConstantPool:
    """Пул констант класса: записи хранятся сырыми байтами, кроме Utf8."""

    def __init__(self, count, entries, tail, minor=0, major=0):
        self.count = count
        self.entries = entries  # список: (tag, payload) или None для второго слота
        self.tail = tail  # файл целиком после пула
        self.minor = minor  # версия формата, сохраняется при пересборке
        self.major = major

    def string_constants(self):
        """Строковые литералы кода: записи тега String (8) и их содержимое.

        Именно они попадают в UI. Имена полей, дескрипторы методов и названия
        классов лежат в других записях пула и переводить их нельзя.
        """
        found = []
        for idx, entry in enumerate(self.entries):
            if entry and entry[0] == 8:  # CONSTANT_String: u2 -> индекс Utf8
                utf8_index = struct.unpack(">H", entry[1])[0]
                target = (
                    self.entries[utf8_index] if utf8_index < len(self.entries) else None
                )
                if target and target[0] == 1:
                    found.append((idx, from_mutf8(target[1][2:])))
        return found

    def methods_using_string_comparison(self):
        """Строковые константы методов, где строка сравнивается.

        Если метод вызывает String.equals или String.hashCode, его строковые
        константы участвуют в сравнении: это ключи (настройки, типы материалов),
        и переводить их нельзя. Метод разбирается по инструкциям, а не по
        соседству в пуле, — это единственный надёжный признак ключа.
        """
        from codescan import scan_string_comparisons

        return scan_string_comparisons(self)

    def utf8_values(self):
        """Все строки пула с номерами записей (payload хранит длину в первых байтах)."""
        found = []
        for idx, entry in enumerate(self.entries, start=1):
            if entry and entry[0] == 1:
                found.append((idx, from_mutf8(entry[1][2:])))
        return found

    def serialize(self):
        """Пересобрать файл класса с текущими записями пула."""
        parts = [
            MAGIC,
            struct.pack(">HH", self.minor, self.major),
            struct.pack(">H", self.count),
        ]
        for entry in self.entries:
            if entry is None:
                continue
            tag, payload = entry
            parts.append(bytes([tag]))
            parts.append(payload)
        parts.append(self.tail)
        return b"".join(parts)

    def replace_utf8(self, mapping, report=None):
        """Заменить строки по словарю original → translation.

        Возвращает число выполненных замен. Строки, которых нет в пуле,
        попадают в report['missing'] — это способ заметить перевод,
        потерявший актуальность после обновления игры.
        """
        # отчёт считаем ДО замены, иначе только что переведённые строки
        # сочтутся отсутствующими в собственном пуле
        if report is not None:
            present = {value for _, value in self.string_constants()}
            report["missing"] = sorted(k for k in mapping if k not in present)
        changed = 0
        for idx, entry in enumerate(self.entries):
            if not entry or entry[0] != 1:
                continue
            original = from_mutf8(entry[1][2:])
            if original in mapping:
                new_bytes = to_mutf8(mapping[original])
                if len(new_bytes) > 0xFFFF:
                    raise ValueError(f"строка длиннее 65535 байт: {original!r}")
                self.entries[idx] = (1, struct.pack(">H", len(new_bytes)) + new_bytes)
                changed += 1
        if report is not None:
            report["changed"] = changed
        return changed


def parse(data):
    """Разобрать .class на пул констант и хвост."""
    if data[:4] != MAGIC:
        raise ValueError("не .class: неверная магия")
    minor, major = struct.unpack(">HH", data[4:8])
    count = struct.unpack(">H", data[8:10])[0]
    entries = [None] * count
    pos = 10
    idx = 1
    while idx < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            length = struct.unpack(">H", data[pos : pos + 2])[0]
            end = pos + 2 + length
            # длину храним вместе с байтами, иначе пересборка теряет два байта на строку
            entries[idx] = (tag, data[pos:end])
            pos = end
            idx += 1
            continue
        size = TAG_SIZE.get(tag) or FIXED_SIZE[tag]
        entries[idx] = (tag, data[pos : pos + size])
        pos += size
        # Long и Double занимают два слота, второй остаётся None и пропускается циклом
        idx += 2 if tag in WIDE_TAGS else 1
    return ConstantPool(count, entries, data[pos:], minor, major)
