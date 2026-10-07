"""Поиск строк, участвующих в сравнении, по инструкциям байткода.

Признак ключа единственный надёжный: метод вызывает String.equals или
String.hashCode. Тогда его строковые константы участвуют в сравнении —
это ключи настроек, имён файлов и типов материалов. Переводить их нельзя.

Разбираются тело класса после пула: поля, методы, атрибуты, и внутри
Code атрибута — инструкции, где ищутся вызовы сравнения и все ldc-константы.
"""

import struct

# Ссылки на методы сравнения строк
COMPARE_METHODS = (
    "java/lang/String.equals",
    "java/lang/String.hashCode",
    "java/lang/String.equalsIgnoreCase",
    "java/lang/String.compareTo",
)


# Размер операнда каждой инструкции в байтах; 0 — операнда нет
def _build_operand_sizes():
    """Размер операнда каждой инструкции в байтах по спецификации JVM (JVMS 6.5).

    Отрицательные значения означают, что длина вычисляется на месте:
    -1 — инструкция switch, -2 — wide.
    """
    sizes = {}
    for op in range(0x00, 0x10):  # nop, aconst_null, константы
        sizes[op] = 0
    sizes.update({0x10: 1, 0x11: 2, 0x12: 1, 0x13: 2, 0x14: 2})
    for op in range(0x15, 0x1A):  # iload..aload с индексом
        sizes[op] = 1
    for op in range(0x1A, 0x36):  # iload_0..aload_3 без операнда
        sizes[op] = 0
    for op in range(0x36, 0x3B):  # istore..astore с индексом
        sizes[op] = 1
    for op in range(0x3B, 0x84):  # istore_0.., стек, арифметика
        sizes[op] = 0
    sizes[0x84] = 2  # iinc: индекс и константа по одному байту
    for op in range(0x85, 0x99):  # преобразования и сравнения
        sizes[op] = 0
    for op in range(0x99, 0xA9):  # if<cond>, goto, jsr
        sizes[op] = 2
    sizes[0xA9] = 1  # ret
    sizes[0xAA] = -1  # tableswitch
    sizes[0xAB] = -1  # lookupswitch
    for op in range(0xAC, 0xB2):  # ireturn..return
        sizes[op] = 0
    for op in range(0xB2, 0xB9):  # getstatic..invokestatic
        sizes[op] = 2
    sizes[0xB9] = 4  # invokeinterface
    sizes[0xBA] = 4  # invokedynamic
    sizes[0xBB] = 2  # new
    sizes[0xBC] = 1  # newarray
    sizes[0xBD] = 2  # anewarray
    sizes[0xBE] = 0  # arraylength
    sizes[0xBF] = 0  # athrow
    sizes[0xC0] = 2  # checkcast
    sizes[0xC1] = 2  # instanceof
    sizes[0xC2] = 0  # monitorenter
    sizes[0xC3] = 0  # monitorexit
    sizes[0xC4] = -2  # wide
    sizes[0xC5] = 3  # multianewarray
    sizes[0xC6] = 2  # ifnull
    sizes[0xC7] = 2  # ifnonnull
    sizes[0xC8] = 4  # goto_w
    sizes[0xC9] = 4  # jsr_w
    return sizes


CMP = _build_operand_sizes()


def _method_ref_name(pool, index):
    """Имя метода по номеру записи Methodref в пуле."""
    entry = pool.entries[index] if index < len(pool.entries) else None
    if not entry or entry[0] not in (9, 10, 11):
        return None
    class_index, nat_index = struct.unpack(">HH", entry[1])
    nat = pool.entries[nat_index] if nat_index < len(pool.entries) else None
    if not nat or nat[0] != 12:
        return None
    name_index = struct.unpack(">H", nat[1][:2])[0]
    target = pool.entries[name_index] if name_index < len(pool.entries) else None
    if not target or target[0] != 1:
        return None
    from classfile import from_mutf8

    return from_mutf8(target[1][2:])


def _string_at(pool, index):
    """Значение константы String по её номеру записи."""
    entry = pool.entries[index] if index < len(pool.entries) else None
    if not entry or entry[0] != 8:
        return None
    utf8_index = struct.unpack(">H", entry[1])[0]
    target = pool.entries[utf8_index] if utf8_index < len(pool.entries) else None
    if not target or target[0] != 1:
        return None
    from classfile import from_mutf8

    return from_mutf8(target[1][2:])


def code_end(code):
    """Смещение сразу за последней инструкцией метода.

    Значение обязано совпасть с длиной кода: это признак того, что разбор
    идёт по настоящим границам инструкций, а не по скользящему окну.
    """
    end = None
    for _offset, _opcode in _iter_instructions(code):
        end = _offset
    if end is None:
        return 0  # у метода нет инструкций вовсе
    return end + _instruction_length(code, end)


def _instruction_length(code, pos):
    """Длина инструкции, начинающейся в pos."""
    opcode = code[pos]
    size_needed = CMP.get(opcode)
    if size_needed is None:
        raise ValueError(f"неизвестный опкод 0x{opcode:02x} на смещении {pos}")
    if size_needed == -1:
        pad = (4 - ((pos + 1) % 4)) % 4
        base = pos + 1 + pad
        if opcode == 0xAA:
            low, high = struct.unpack(">ii", code[base + 4 : base + 12])
            return base + 12 + 4 * (high - low + 1) - pos
        npairs = struct.unpack(">i", code[base + 4 : base + 8])[0]
        return base + 8 + 8 * npairs - pos
    if size_needed == -2:
        return 1 + (4 if code[pos + 1] == 0x84 else 2)
    return 1 + size_needed


def _iter_instructions(code):
    """Пройти код метода по границам инструкций и отдать (смещение, опкод).

    Границы обязаны сойтись ровно к концу массива: иначе разбор съезжает и
    находит несуществующие ключи. Это проверяется отдельным оракулом по всем
    методам игры.
    """
    pos = 0
    size = len(code)
    while pos < size:
        opcode = code[pos]
        yield pos, opcode
        size_needed = CMP.get(opcode)
        if size_needed is None:
            raise ValueError(f"неизвестный опкод 0x{opcode:02x} на смещении {pos}")
        if size_needed == -1:  # tableswitch или lookupswitch
            # после опкода идёт выравнивание до 4 байт от начала метода
            pad = (4 - ((pos + 1) % 4)) % 4
            base = pos + 1 + pad
            if opcode == 0xAA:  # tableswitch: default, low, high, затем переходы
                low, high = struct.unpack(">ii", code[base + 4 : base + 12])
                count = high - low + 1
                pos = base + 12 + 4 * count
            else:  # lookupswitch: default, npairs, затем пары ключ-переход
                npairs = struct.unpack(">i", code[base + 4 : base + 8])[0]
                pos = base + 8 + 8 * npairs
        elif size_needed == -2:  # wide: индекс и следующий опкод
            pos += 1 + (4 if code[pos + 1] == 0x84 else 2)
        else:
            pos += 1 + size_needed
        if pos > size:
            raise ValueError(
                f"инструкция 0x{opcode:02x} на {pos - size - 1} выходит за конец кода"
            )


COMPARE_NAMES = (
    "equals",
    "equalsIgnoreCase",
    "compareTo",
    "contains",
    "startsWith",
    "endsWith",
    "indexOf",
    "lastIndexOf",
)

# Методы, которым передают имя проверяемого объекта в файле. Строки рядом с
# ними — ключи структуры, даже если сравнения строк рядом не было:
# assertNextObject(reader, "preferences") проверяет имя объекта в JSON.
NAME_CHECKERS = ("assertNextObject", "testNextObject")

# Столько инструкций между загрузкой литерала и сравнением считаются соседними.
# В switch по строке компилятор кладёт рядом с equals ровно литерал-ключ.
NEIGHBOUR_WINDOW = 4


def _scan_code(pool, code):
    """Строковые литералы, которые являются аргументом сравнения.

    Признак узкий: литерал загружен инструкцией ldc и в следующие несколько
    инструкций вызывается equals/contains/startsWith. Именно так выглядит
    switch по строке и проверка ключа настроек. Строки того же метода, что
    не участвуют в сравнении (подписи интерфейса), остаются переводимыми.
    """
    found = set()
    pending = None  # (значение, сколько инструкций назад загружено)
    distance = 0
    for offset, opcode in _iter_instructions(code):
        distance += 1
        value = None
        if opcode == 0x12:
            value = _string_at(pool, code[offset + 1])
        elif opcode in (0x13, 0x14):
            value = _string_at(
                pool, struct.unpack(">H", code[offset + 1 : offset + 3])[0]
            )
        if value is not None:
            pending, distance = value, 0
            continue
        if opcode in (0xB6, 0xB7, 0xB8, 0xB9):
            index = struct.unpack(">H", code[offset + 1 : offset + 3])[0]
            name = _method_ref_name(pool, index)
            if (
                (name in COMPARE_NAMES or name in NAME_CHECKERS)
                and pending is not None
                and distance <= NEIGHBOUR_WINDOW
            ):
                found.add(pending)
            # любой вызов стирает «кандидата»: литерал уже израсходован
            pending, distance = None, 0
            continue
        if pending is not None and distance > NEIGHBOUR_WINDOW:
            pending, distance = None, 0
    return found


def scan_string_comparisons(pool):
    """Все строковые константы методов, где строка сравнивается или ищется."""
    found = set()
    data = pool.tail
    pos = 0

    def u2(offset):
        return struct.unpack(">H", data[offset : offset + 2])[0]

    pos += 6  # access_flags, this_class, super_class
    interfaces = u2(pos)
    pos += 2 + 2 * interfaces

    def skip_members(offset):
        """Пройти поля или методы, отдавая смещения атрибутов Code."""
        count = u2(offset)
        offset += 2
        codes = []
        for _ in range(count):
            offset += 6  # access_flags, name_index, descriptor_index
            attrs = u2(offset)
            offset += 2
            for _ in range(attrs):
                name_index = u2(offset)
                length = struct.unpack(">I", data[offset + 2 : offset + 6])[0]
                target = pool.entries[name_index]
                if target and target[0] == 1:
                    from classfile import from_mutf8

                    if from_mutf8(target[1][2:]) == "Code":
                        codes.append(offset + 6)
                offset += 6 + length
        return offset, codes

    pos, _ = skip_members(pos)
    pos, code_offsets = skip_members(pos)
    for attr_start in code_offsets:
        # Структура Code: u2 max_stack, u2 max_locals, u4 code_length, u1 code[]
        code_length = struct.unpack(">I", data[attr_start + 4 : attr_start + 8])[0]
        code = data[attr_start + 8 : attr_start + 8 + code_length]
        found.update(_scan_code(pool, code))
    return found
