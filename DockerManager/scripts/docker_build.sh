#!/bin/bash
# Скрипт сборки бинарного файла в Docker контейнере
# Версия: V3.1.164 (2025.12.07)
# Компания: ООО "НПА Вира-Реалтайм"
# Разработчик: @FoksSegr & AI Assistant (@LLM)

set -e
export PATH="/usr/local/bin:$PATH"

cd /build
mkdir -p bin build

# Проверяем tkinter
echo "[#] Проверка tkinter..."
python3 -c "import tkinter; print('[OK] tkinter доступен')"

# КРИТИЧНО: Сначала исправляем __future__ импорты в объединенном файле
echo "[#] Исправление __future__ импортов (ПЕРВЫМ ДЕЛОМ)..." >&2
python3 /build/DockerManager/scripts/fix_future_imports.py

# Определяем имя входного и выходного файла из переменной окружения
INPUT_FILE="${INPUT_FILE:-FSA-AstraInstall.py}"
OUTPUT_NAME="${OUTPUT_NAME:-FSA-AstraInstall}"

# Добавляем суффикс платформы к имени выходного файла
PLATFORM_NAME="${PLATFORM_NAME:-}"
if [ -n "$PLATFORM_NAME" ]; then
    # Извлекаем номер версии из имени платформы (astra-1.7 -> 1-7, astra-1.8 -> 1-8)
    # Заменяем точку на дефис, чтобы избежать проблем с расширением файла
    PLATFORM_VERSION=$(echo "$PLATFORM_NAME" | sed 's/astra-//' | sed 's/\./-/g')
    if [ -n "$PLATFORM_VERSION" ]; then
        OUTPUT_NAME="${OUTPUT_NAME}-${PLATFORM_VERSION}"
        echo "[#] Имя выходного файла с суффиксом платформы: ${OUTPUT_NAME}" >&2
    fi
fi

# Проверяем наличие входного файла
if [ ! -f "${INPUT_FILE}" ]; then
    echo "[ERROR] Входной файл не найден: ${INPUT_FILE}" >&2
    exit 1
fi

# Проверка иконки
ICON_FILE="/build/Icons/fly-astra-update.png"
ICON_PARAM=""
ICON_DATA_PARAM=""

if [ -f "$ICON_FILE" ]; then
    ICON_PARAM="--icon $ICON_FILE"
    # Добавляем иконку как ресурс для доступа из кода
    ICON_DATA_PARAM="--add-data $ICON_FILE:Icons"
    echo "[#] Использование иконки: $ICON_FILE" >&2
    # Проверяем размер файла для информации
    ICON_SIZE=$(stat -f%z "$ICON_FILE" 2>/dev/null || stat -c%s "$ICON_FILE" 2>/dev/null || echo "unknown")
    echo "[#] Размер файла иконки: $ICON_SIZE байт" >&2
else
    echo "[WARNING] Иконка не найдена: $ICON_FILE, сборка без иконки" >&2
fi

# КРИТИЧНО: Находим библиотеки Tcl/Tk для включения в бинарник
# PyInstaller не включает системные библиотеки автоматически
# Нужны: 1) Tcl/Tk скрипты (в /usr/share/tcltk/) 2) Скомпилированные библиотеки .so (в /usr/lib/)
# Универсальный поиск без привязки к конкретной версии
TCL_LIB_DIR=""
TK_LIB_DIR=""
TCL_SO_LIB=""
TK_SO_LIB=""

# Ищем библиотеки Tcl в /usr/share/tcltk (любая версия: tcl8.6, tcl8.7 и т.д.)
for tcl_dir in /usr/share/tcltk/tcl*; do
    if [ -d "$tcl_dir" ] && [ -f "$tcl_dir/init.tcl" ]; then
        TCL_LIB_DIR="$tcl_dir"
        echo "[#] Найдена библиотека Tcl (скрипты): $TCL_LIB_DIR" >&2
        break
    fi
done

# Ищем библиотеки Tk в /usr/share/tcltk (любая версия: tk8.6, tk8.7 и т.д.)
for tk_dir in /usr/share/tcltk/tk*; do
    if [ -d "$tk_dir" ] && [ -f "$tk_dir/tk.tcl" ]; then
        TK_LIB_DIR="$tk_dir"
        echo "[#] Найдена библиотека Tk (скрипты): $TK_LIB_DIR" >&2
        break
    fi
done

# Ищем скомпилированные библиотеки Tcl (.so) в /usr/lib/
for tcl_so in /usr/lib/x86_64-linux-gnu/libtcl*.so* /usr/lib/libtcl*.so*; do
    if [ -f "$tcl_so" ] && [ ! -L "$tcl_so" ]; then
        # Берем реальный файл, а не симлинк
        TCL_SO_LIB="$tcl_so"
        echo "[#] Найдена библиотека Tcl (.so): $TCL_SO_LIB" >&2
        break
    fi
done

# Ищем скомпилированные библиотеки Tk (.so) в /usr/lib/
for tk_so in /usr/lib/x86_64-linux-gnu/libtk*.so* /usr/lib/libtk*.so*; do
    if [ -f "$tk_so" ] && [ ! -L "$tk_so" ]; then
        # Берем реальный файл, а не симлинк
        TK_SO_LIB="$tk_so"
        echo "[#] Найдена библиотека Tk (.so): $TK_SO_LIB" >&2
        break
    fi
done

# КРИТИЧНО: Ищем библиотеку BLT (зависимость tkinter)
# libBLT находится в /usr/lib/, а не в /usr/lib/x86_64-linux-gnu/
BLT_SO_LIB=""
for blt_so in /usr/lib/libBLT*.so* /usr/lib/x86_64-linux-gnu/libBLT*.so*; do
    if [ -f "$blt_so" ] && [ ! -L "$blt_so" ]; then
        # Берем реальный файл, а не симлинк
        BLT_SO_LIB="$blt_so"
        echo "[#] Найдена библиотека BLT (.so): $BLT_SO_LIB" >&2
        break
    fi
done

# Формируем параметры для включения библиотек Tcl/Tk
# КРИТИЧНО: PyInstaller с --collect-all tkinter должен создавать _tcl_data и _tk_data,
# но иногда этого не происходит, поэтому явно добавляем директории
# КРИТИЧНО: Используем --add-data для директорий со скриптами
# КРИТИЧНО: Используем --add-binary для скомпилированных библиотек .so
TCL_TK_DATA=""
TCL_TK_BINARY=""

# КРИТИЧНО: НЕ добавляем директории Tcl/Tk через --add-data
# Явное добавление через --add-data с именами _tcl_data и _tk_data ломает base_library.zip
# Используем только --collect-all tkinter, который должен создать эти директории
# if [ -n "$TCL_LIB_DIR" ] && [ -d "$TCL_LIB_DIR" ]; then
#     TCL_TK_DATA="$TCL_TK_DATA --add-data \"$TCL_LIB_DIR:_tcl_data\""
#     echo "[#] Включаем в бинарник (скрипты Tcl): $TCL_LIB_DIR -> _tcl_data" >&2
# fi
# if [ -n "$TK_LIB_DIR" ] && [ -d "$TK_LIB_DIR" ]; then
#     TCL_TK_DATA="$TCL_TK_DATA --add-data \"$TK_LIB_DIR:_tk_data\""
#     echo "[#] Включаем в бинарник (скрипты Tk): $TK_LIB_DIR -> _tk_data" >&2
# fi

# КРИТИЧНО: Явно включаем все .so библиотеки Tcl/Tk
# PyInstaller с --collect-binaries tkinter должен собирать их, но для надёжности добавляем явно
if [ -n "$TCL_SO_LIB" ] && [ -f "$TCL_SO_LIB" ]; then
    TCL_SO_NAME=$(basename "$TCL_SO_LIB")
    TCL_TK_BINARY="$TCL_TK_BINARY --add-binary \"$TCL_SO_LIB:.\""
    echo "[#] Включаем в бинарник (.so Tcl): $TCL_SO_LIB -> $TCL_SO_NAME" >&2
fi
if [ -n "$TK_SO_LIB" ] && [ -f "$TK_SO_LIB" ]; then
    TK_SO_NAME=$(basename "$TK_SO_LIB")
    TCL_TK_BINARY="$TCL_TK_BINARY --add-binary \"$TK_SO_LIB:.\""
    echo "[#] Включаем в бинарник (.so Tk): $TK_SO_LIB -> $TK_SO_NAME" >&2
fi
# КРИТИЧНО: Включаем библиотеку BLT (зависимость tkinter)
if [ -n "$BLT_SO_LIB" ] && [ -f "$BLT_SO_LIB" ]; then
    BLT_SO_NAME=$(basename "$BLT_SO_LIB")
    TCL_TK_BINARY="$TCL_TK_BINARY --add-binary \"$BLT_SO_LIB:.\""
    echo "[#] Включаем в бинарник (.so): $BLT_SO_LIB -> $BLT_SO_NAME" >&2
fi

# КРИТИЧНО: Включаем wmctrl для активации окон
WMCTRL_BINARY=""
WMCTRL_PATH=$(which wmctrl 2>/dev/null || echo "")
if [ -n "$WMCTRL_PATH" ] && [ -f "$WMCTRL_PATH" ]; then
    WMCTRL_BINARY="--add-binary \"$WMCTRL_PATH:.\""
    echo "[#] Включаем в бинарник (wmctrl): $WMCTRL_PATH -> wmctrl" >&2
else
    echo "[WARNING] wmctrl не найден, активация окон будет недоступна" >&2
fi

# КРИТИЧНО: Ищем и включаем C-модуль _tkinter (обязательно для работы tkinter)
# Пытаемся найти через Python (самый надёжный способ)
TKINTER_SO=""
if python3 -c "import _tkinter" 2>/dev/null; then
    TKINTER_SO=$(python3 -c "import _tkinter; import os; print(os.path.abspath(_tkinter.__file__))" 2>/dev/null || echo "")
    if [ -n "$TKINTER_SO" ] && [ -f "$TKINTER_SO" ]; then
        echo "[#] Найден C-модуль _tkinter через Python: $TKINTER_SO" >&2
    else
        TKINTER_SO=""
    fi
fi

# Если не нашли через Python, ищем вручную
if [ -z "$TKINTER_SO" ]; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3.11")
    for tkinter_so in /usr/lib/python${PYTHON_VERSION}/lib-dynload/_tkinter*.so \
                      /usr/lib/python3.*/lib-dynload/_tkinter*.so \
                      /usr/lib/python3.*/lib-dynload/_tkinter.cpython*.so; do
        if [ -f "$tkinter_so" ]; then
            TKINTER_SO="$tkinter_so"
            echo "[#] Найден C-модуль _tkinter вручную: $TKINTER_SO" >&2
            break
        fi
    done
fi

if [ -n "$TKINTER_SO" ] && [ -f "$TKINTER_SO" ]; then
    # КРИТИЧНО: Включаем _tkinter.so в правильную структуру Python
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3.11")
    TCL_TK_BINARY="$TCL_TK_BINARY --add-binary \"$TKINTER_SO:python${PYTHON_VERSION}/lib-dynload\""
    echo "[#] Включаем C-модуль _tkinter в бинарник: $TKINTER_SO -> python${PYTHON_VERSION}/lib-dynload" >&2
else
    echo "[ERROR] C-модуль _tkinter не найден! tkinter не будет работать!" >&2
    echo "[ERROR] Проверьте, что установлен пакет python3-tk" >&2
    exit 1
fi

# КРИТИЧНО: Проверяем только критичные компоненты (библиотеки .so)
# Скрипты Tcl/Tk будут собраны через --collect-all tkinter
MISSING_COMPONENTS=""
if [ -z "$TCL_SO_LIB" ] || [ ! -f "$TCL_SO_LIB" ]; then
    MISSING_COMPONENTS="$MISSING_COMPONENTS Tcl библиотека (.so)"
fi
if [ -z "$TK_SO_LIB" ] || [ ! -f "$TK_SO_LIB" ]; then
    MISSING_COMPONENTS="$MISSING_COMPONENTS Tk библиотека (.so)"
fi
if [ -z "$BLT_SO_LIB" ] || [ ! -f "$BLT_SO_LIB" ]; then
    echo "[WARNING] BLT библиотека не найдена (не критично, но может потребоваться)" >&2
fi

if [ -n "$MISSING_COMPONENTS" ]; then
    echo "[ERROR] Не найдены необходимые компоненты для tkinter: $MISSING_COMPONENTS" >&2
    echo "[ERROR] Проверьте установку пакетов: python3-tk tk-dev tcl-dev tcl tcl8.6 tk tk8.6" >&2
    exit 1
fi

echo "[#] ✓ Критичные компоненты Tcl/Tk найдены" >&2
echo "[#] Скрипты Tcl/Tk будут собраны через --collect-all tkinter" >&2

# Компилируем объединенный файл
# Включаем все необходимые модули для полной функциональности
echo "[#] Компиляция ${INPUT_FILE} в ${OUTPUT_NAME}..."
# КРИТИЧНО: Проверяем размер и хеш исходного файла для подтверждения актуальности
INPUT_SIZE=$(stat -c%s "${INPUT_FILE}" 2>/dev/null || stat -f%z "${INPUT_FILE}" 2>/dev/null || echo "unknown")
INPUT_HASH=$(md5sum "${INPUT_FILE}" 2>/dev/null | cut -d' ' -f1 || sha256sum "${INPUT_FILE}" 2>/dev/null | cut -d' ' -f1 || echo "unknown")
INPUT_LINES=$(wc -l < "${INPUT_FILE}" 2>/dev/null || echo "unknown")
echo "[#] Размер исходного файла: ${INPUT_SIZE} байт"
echo "[#] Хеш исходного файла: ${INPUT_HASH}"
echo "[#] Строк в файле: ${INPUT_LINES}"
# КРИТИЧНО: Полная очистка кэша PyInstaller перед сборкой
echo "[#] Очистка кэша PyInstaller..."
rm -rf build dist *.spec 2>/dev/null || true
rm -rf ~/.cache/pyinstaller 2>/dev/null || true
rm -rf /root/.cache/pyinstaller 2>/dev/null || true
# КРИТИЧНО: Проверяем, что исходный файл существует и не пустой
if [ ! -f "${INPUT_FILE}" ]; then
    echo "[ERROR] Исходный файл не найден: ${INPUT_FILE}"
    exit 1
fi
if [ ! -s "${INPUT_FILE}" ]; then
    echo "[ERROR] Исходный файл пустой: ${INPUT_FILE}"
    exit 1
fi
# КРИТИЧНО: Проверяем наличие runtime hook для предзагрузки libBLT
RUNTIME_HOOK="/build/DockerManager/scripts/pyi_rth_libblt.py"
RUNTIME_HOOK_PARAM=""
if [ -f "$RUNTIME_HOOK" ]; then
    RUNTIME_HOOK_PARAM="--runtime-hook $RUNTIME_HOOK"
    echo "[#] Использование runtime hook для предзагрузки libBLT: $RUNTIME_HOOK" >&2
else
    echo "[WARNING] Runtime hook не найден: $RUNTIME_HOOK" >&2
fi

# КРИТИЧНО: Создаём hook-файл для tkinter, чтобы PyInstaller явно включил C-модуль и данные Tcl/Tk
PYINSTALLER_HOOKS_DIR="/build/build/pyinstaller_hooks"
mkdir -p "$PYINSTALLER_HOOKS_DIR"
HOOK_TKINTER_FILE="$PYINSTALLER_HOOKS_DIR/hook-tkinter.py"
HOOKS_DIR_PARAM=""
# Создаём hook-файл с явным указанием путей к _tkinter.so и директориям Tcl/Tk
if [ -n "$TKINTER_SO" ] && [ -f "$TKINTER_SO" ]; then
    # Формируем список datas для включения директорий Tcl/Tk
    DATAS_LIST=""
    if [ -n "$TCL_LIB_DIR" ] && [ -d "$TCL_LIB_DIR" ]; then
        DATAS_LIST="    ('$TCL_LIB_DIR', '_tcl_data'),"
        echo "[#] Hook включит директорию Tcl: $TCL_LIB_DIR -> _tcl_data" >&2
    fi
    if [ -n "$TK_LIB_DIR" ] && [ -d "$TK_LIB_DIR" ]; then
        DATAS_LIST="${DATAS_LIST}\n    ('$TK_LIB_DIR', '_tk_data'),"
        echo "[#] Hook включит директорию Tk: $TK_LIB_DIR -> _tk_data" >&2
    fi
    
    # Создаём hook-файл с явным указанием путей
    cat > "$HOOK_TKINTER_FILE" << EOF
# Hook для tkinter - явно включаем C-модуль и данные Tcl/Tk
import os

binaries = []
tkinter_so = "$TKINTER_SO"
if os.path.exists(tkinter_so):
    binaries.append((tkinter_so, 'python3.11/lib-dynload'))

# КРИТИЧНО: Явно добавляем директории Tcl/Tk через datas
# Это гарантирует, что _tcl_data и _tk_data будут созданы в бинарнике
datas = []
$(if [ -n "$TCL_LIB_DIR" ] && [ -d "$TCL_LIB_DIR" ]; then echo "if os.path.exists('$TCL_LIB_DIR'):"; echo "    datas.append(('$TCL_LIB_DIR', '_tcl_data'))"; fi)
$(if [ -n "$TK_LIB_DIR" ] && [ -d "$TK_LIB_DIR" ]; then echo "if os.path.exists('$TK_LIB_DIR'):"; echo "    datas.append(('$TK_LIB_DIR', '_tk_data'))"; fi)
EOF
    echo "[#] Создан hook-файл для tkinter: $HOOK_TKINTER_FILE" >&2
    HOOKS_DIR_PARAM="--additional-hooks-dir $PYINSTALLER_HOOKS_DIR"
fi

# КРИТИЧНО: Используем eval для правильной обработки кавычек в параметрах
# УБРАНЫ все избыточные --hidden-import для стандартных библиотек (PyInstaller включает их автоматически)
# УБРАНЫ все избыточные --hidden-import для tkinter (--collect-all tkinter включает всё)
# УБРАНЫ избыточные --collect-submodules, --collect-binaries, --collect-data (уже в --collect-all)
eval pyinstaller --onefile --console \
    $ICON_PARAM \
    $ICON_DATA_PARAM \
    $TCL_TK_BINARY \
    $WMCTRL_BINARY \
    $RUNTIME_HOOK_PARAM \
    $HOOKS_DIR_PARAM \
    --name "${OUTPUT_NAME}" \
    --distpath . \
    --workpath build \
    --specpath build \
    --clean \
    --noconfirm \
    --hidden-import psutil \
    --collect-all psutil \
    --collect-all tkinter \
    "${INPUT_FILE}"

# Устанавливаем права на выполнение
chmod +x "${OUTPUT_NAME}" 2>/dev/null || true

echo "[OK] Сборка завершена"
echo "[OK] Создан файл: ${OUTPUT_NAME}"

# КРИТИЧНО: Проверяем содержимое бинарника после сборки
echo "[#] Проверка содержимого бинарника..." >&2
BINARY_SIZE=$(stat -c%s "${OUTPUT_NAME}" 2>/dev/null || stat -f%z "${OUTPUT_NAME}" 2>/dev/null || echo "unknown")
echo "[#] Размер бинарника: ${BINARY_SIZE} байт" >&2

# Пытаемся проверить содержимое через PyInstaller (если доступен)
if command -v pyi-archive_viewer >/dev/null 2>&1; then
    echo "[#] Проверка содержимого через pyi-archive_viewer..." >&2
    # Проверяем наличие критичных директорий и файлов
    if pyi-archive_viewer "${OUTPUT_NAME}" 2>/dev/null | grep -q "_tcl_data"; then
        echo "[#] ✓ _tcl_data найдена в бинарнике" >&2
    else
        echo "[#] ❌ _tcl_data НЕ найдена в бинарнике!" >&2
    fi
    
    if pyi-archive_viewer "${OUTPUT_NAME}" 2>/dev/null | grep -q "_tk_data"; then
        echo "[#] ✓ _tk_data найдена в бинарнике" >&2
    else
        echo "[#] ❌ _tk_data НЕ найдена в бинарнике!" >&2
    fi
    
    # Проверяем наличие .so библиотек
    if pyi-archive_viewer "${OUTPUT_NAME}" 2>/dev/null | grep -q "libtcl.*\.so"; then
        echo "[#] ✓ Библиотека libtcl*.so найдена в бинарнике" >&2
    else
        echo "[#] ❌ Библиотека libtcl*.so НЕ найдена в бинарнике!" >&2
    fi
    
    if pyi-archive_viewer "${OUTPUT_NAME}" 2>/dev/null | grep -q "libtk.*\.so"; then
        echo "[#] ✓ Библиотека libtk*.so найдена в бинарнике" >&2
    else
        echo "[#] ❌ Библиотека libtk*.so НЕ найдена в бинарнике!" >&2
    fi
    
    if pyi-archive_viewer "${OUTPUT_NAME}" 2>/dev/null | grep -q "_tkinter.*\.so"; then
        echo "[#] ✓ C-модуль _tkinter*.so найден в бинарнике" >&2
    else
        echo "[#] ❌ C-модуль _tkinter*.so НЕ найден в бинарнике!" >&2
    fi
    
    # Проверяем наличие wmctrl в бинарнике
    if pyi-archive_viewer "${OUTPUT_NAME}" 2>/dev/null | grep -q "wmctrl"; then
        echo "[#] ✓ wmctrl найден в бинарнике" >&2
    else
        echo "[#] ❌ wmctrl НЕ найден в бинарнике!" >&2
    fi
else
    echo "[#] pyi-archive_viewer недоступен, пропускаем проверку содержимого" >&2
    echo "[#] Для проверки запустите бинарник и проверьте вывод [RUNTIME_HOOK] и [DEBUG]" >&2
fi

