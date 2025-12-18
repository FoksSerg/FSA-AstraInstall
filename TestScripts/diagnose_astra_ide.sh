#!/bin/bash
# -*- coding: utf-8 -*-
#
# Скрипт диагностики запуска Astra.IDE
# Собирает все ошибки и логи в один файл
# Версия: 1.0
# Компания: ООО "НПА Вира-Реалтайм"
#

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Создаем директорию для логов СРАЗУ
# Логи сохраняются в домашней директории пользователя
LOG_DIR="${HOME}/astra-ide-diagnostics"
mkdir -p "${LOG_DIR}" || {
    echo "ОШИБКА: Не удалось создать директорию для логов: ${LOG_DIR}" >&2
    exit 1
}

# Имя файла лога с временной меткой
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/astra-ide-diagnostics_${TIMESTAMP}.log"
ERROR_LOG="${LOG_DIR}/astra-ide-errors_${TIMESTAMP}.log"
WINE_LOG="${LOG_DIR}/wine-debug_${TIMESTAMP}.log"

# Начинаем логирование СРАЗУ с самого начала
# Выводим информацию на экран И в лог одновременно
{
    echo "=========================================="
    echo "Диагностика запуска Astra.IDE"
    echo "Версия скрипта: 1.0"
    echo "Время запуска: $(date)"
    echo "Пользователь: $(whoami)"
    echo "Домашняя директория: ${HOME}"
    echo ""
    echo "📁 ДИРЕКТОРИЯ ЛОГОВ: ${LOG_DIR}"
    echo "📄 Основной лог: ${LOG_FILE}"
    echo "❌ Лог ошибок: ${ERROR_LOG}"
    echo "🍷 Лог Wine: ${WINE_LOG}"
    echo ""
    echo "=========================================="
    echo ""
    echo "[INIT] Инициализация логирования..."
    echo "[INIT] Все команды будут записаны в лог-файлы"
    echo "[INIT] Логи сохраняются в: ${LOG_DIR}"
    echo ""
} | tee "${LOG_FILE}"

# Функция для логирования (теперь LOG_FILE уже создан)
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}" | tee -a "${ERROR_LOG}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${LOG_FILE}"
}

# Логируем информацию о запуске
log_info "Скрипт диагностики запущен"
log_info "Логи будут сохранены в: ${LOG_DIR}"
log_info "Аргументы командной строки: $*"
log_info "PID процесса: $$"
log_info "Рабочая директория: $(pwd)"

# 1. Информация о системе
log_info "Сбор информации о системе..."
{
    echo "=== ИНФОРМАЦИЯ О СИСТЕМЕ ==="
    echo "ОС: $(uname -a)"
    echo "Пользователь: $(whoami)"
    echo "Домашняя директория: ${HOME}"
    echo "Время: $(date)"
    echo ""
    echo "=== ИНФОРМАЦИЯ О ВИДЕОКАРТЕ ==="
    if command -v lspci &> /dev/null; then
        lspci | grep -i vga || echo "Видеокарта не найдена через lspci"
    else
        echo "lspci не установлен"
    fi
    if [ -f /proc/driver/nvidia/version ]; then
        echo "NVIDIA драйвер: $(cat /proc/driver/nvidia/version)"
    fi
    echo ""
    echo "=== СВОБОДНАЯ ПАМЯТЬ ==="
    free -h
    echo ""
    echo "=== СВОБОДНОЕ МЕСТО НА ДИСКЕ ==="
    df -h "${HOME}"
    echo ""
} | tee -a "${LOG_FILE}"

# 2. Поиск WINEPREFIX
log_info "Поиск WINEPREFIX..."
WINEPREFIX_PATH=""
if [ -d "${HOME}/.wine-astraregul" ]; then
    WINEPREFIX_PATH="${HOME}/.wine-astraregul"
    log_info "Найден WINEPREFIX: ${WINEPREFIX_PATH}"
elif [ -d "${HOME}/.wine" ]; then
    WINEPREFIX_PATH="${HOME}/.wine"
    log_warn "Используется стандартный WINEPREFIX: ${WINEPREFIX_PATH}"
else
    log_error "WINEPREFIX не найден!"
    exit 1
fi

export WINEPREFIX="${WINEPREFIX_PATH}"
log_info "WINEPREFIX установлен: ${WINEPREFIX}"

# 3. Поиск Wine
log_info "Поиск Wine..."
WINE_PATH=""
if [ -f "/opt/wine-astraregul/bin/wine" ]; then
    WINE_PATH="/opt/wine-astraregul/bin/wine"
    log_info "Найден Wine: ${WINE_PATH}"
elif [ -f "/opt/wine-9.0/bin/wine" ]; then
    WINE_PATH="/opt/wine-9.0/bin/wine"
    log_info "Найден Wine: ${WINE_PATH}"
elif command -v wine &> /dev/null; then
    WINE_PATH=$(which wine)
    log_info "Найден Wine в PATH: ${WINE_PATH}"
else
    log_error "Wine не найден!"
    exit 1
fi

export WINE="${WINE_PATH}"

# Проверка версии Wine
log_info "Версия Wine:"
"${WINE_PATH}" --version 2>&1 | tee -a "${LOG_FILE}" || { log_warn "Не удалось получить версию Wine"; true; }

# 4. Поиск Astra.IDE.exe
# Пути взяты из конфигурации компонентов в FSA-AstraInstall.py:
# - Компонент 'astra_ide': 'drive_c/Program Files/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common/Astra.IDE.exe'
# - Ярлык 'astra_desktop_shortcut': executable_path с тем же путем
log_info "Поиск Astra.IDE.exe..."
log_info "Используются пути из конфигурации компонентов FSA-AstraInstall.py"

# Сначала проверяем структуру директорий
ASTRAREGUL_DIR="${WINEPREFIX}/drive_c/Program Files/AstraRegul"
if [ -d "${ASTRAREGUL_DIR}" ]; then
    log_info "Директория AstraRegul найдена: ${ASTRAREGUL_DIR}"
    {
        echo "=== СТРУКТУРА ДИРЕКТОРИИ ASTRAREGUL ==="
        ls -la "${ASTRAREGUL_DIR}" 2>&1 || echo "Не удалось прочитать директорию"
        echo ""
        echo "=== ВЕРСИИ ASTRA.IDE (из структуры директорий) ==="
        find "${ASTRAREGUL_DIR}" -maxdepth 1 -type d -name "Astra.IDE_64_*" 2>&1 | sed 's|.*/||' || echo "Версии не найдены"
        echo ""
        echo "=== ПОИСК ВСЕХ .EXE ФАЙЛОВ В ASTRAREGUL ==="
        find "${ASTRAREGUL_DIR}" -name "*.exe" -type f 2>&1 | head -20 || echo "Не найдено .exe файлов"
        echo ""
    } | tee -a "${LOG_FILE}"
else
    log_warn "Директория AstraRegul не найдена: ${ASTRAREGUL_DIR}"
    {
        echo "=== ЧТО ЕСТЬ В Program Files ==="
        ls -la "${WINEPREFIX}/drive_c/Program Files/" 2>&1 | head -20 || echo "Не удалось прочитать директорию"
        echo ""
    } | tee -a "${LOG_FILE}"
fi

ASTRA_IDE_EXE=""
# Пути из конфигурации компонентов (в порядке приоритета)
# Соответствуют путям в FSA-AstraInstall.py, компонент 'astra_ide'
POSSIBLE_PATHS=(
    # Точный путь для версии 1.7.2.1 (наиболее вероятный)
    "${WINEPREFIX}/drive_c/Program Files/AstraRegul/Astra.IDE_64_1.7.2.1/Astra.IDE/Common/Astra.IDE.exe"
    # Путь с wildcard для версии 1.8.x
    "${WINEPREFIX}/drive_c/Program Files/AstraRegul/Astra.IDE_64_1.8*/Astra.IDE/Common/Astra.IDE.exe"
    # Общий путь с wildcard (из конфигурации компонента)
    "${WINEPREFIX}/drive_c/Program Files/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common/Astra.IDE.exe"
    # Альтернативный путь в Program Files (x86)
    "${WINEPREFIX}/drive_c/Program Files (x86)/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common/Astra.IDE.exe"
)

log_info "Поиск по стандартным путям..."
for path in "${POSSIBLE_PATHS[@]}"; do
    # Раскрываем wildcards
    for expanded_path in ${path}; do
        if [ -f "${expanded_path}" ]; then
            ASTRA_IDE_EXE="${expanded_path}"
            log_info "Найден по стандартному пути: ${ASTRA_IDE_EXE}"
            break 2
        fi
    done
done

# Если не нашли по стандартным путям, ищем через find
if [ -z "${ASTRA_IDE_EXE}" ]; then
    log_info "Поиск через find..."
    if [ -d "${ASTRAREGUL_DIR}" ]; then
        FOUND_EXE=$(find "${ASTRAREGUL_DIR}" -name "Astra.IDE.exe" -type f 2>/dev/null | head -1)
        if [ -n "${FOUND_EXE}" ]; then
            ASTRA_IDE_EXE="${FOUND_EXE}"
            log_info "Найден через find: ${ASTRA_IDE_EXE}"
        fi
    fi
fi

# Пробуем также в Program Files (x86)
if [ -z "${ASTRA_IDE_EXE}" ]; then
    ASTRAREGUL_DIR_X86="${WINEPREFIX}/drive_c/Program Files (x86)/AstraRegul"
    if [ -d "${ASTRAREGUL_DIR_X86}" ]; then
        log_info "Поиск в Program Files (x86)..."
        FOUND_EXE=$(find "${ASTRAREGUL_DIR_X86}" -name "Astra.IDE.exe" -type f 2>/dev/null | head -1)
        if [ -n "${FOUND_EXE}" ]; then
            ASTRA_IDE_EXE="${FOUND_EXE}"
            log_info "Найден в Program Files (x86): ${ASTRA_IDE_EXE}"
        fi
    fi
fi

if [ -z "${ASTRA_IDE_EXE}" ]; then
    log_error "Astra.IDE.exe не найден!"
    log_info "Искали по путям из конфигурации компонентов FSA-AstraInstall.py:"
    for path in "${POSSIBLE_PATHS[@]}"; do
        echo "  - ${path}" | tee -a "${LOG_FILE}"
        # Показываем, что реально есть по этому пути
        for expanded_path in ${path}; do
            if [ -d "$(dirname "${expanded_path}")" ]; then
                echo "    Директория существует: $(dirname "${expanded_path}")" | tee -a "${LOG_FILE}"
                echo "    Содержимое:" | tee -a "${LOG_FILE}"
                ls -la "$(dirname "${expanded_path}")" 2>&1 | head -5 | sed 's/^/      /' | tee -a "${LOG_FILE}" || true
            fi
        done
    done
    {
        echo ""
        echo "=== ДИАГНОСТИКА: ЧТО РЕАЛЬНО ЕСТЬ ==="
        echo "Директория WINEPREFIX: ${WINEPREFIX}"
        echo "Путь из конфигурации: drive_c/Program Files/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common/Astra.IDE.exe"
        echo ""
        echo "Содержимое drive_c/Program Files:"
        ls -la "${WINEPREFIX}/drive_c/Program Files/" 2>&1 | head -30 || echo "Не удалось прочитать"
        echo ""
        if [ -d "${ASTRAREGUL_DIR}" ]; then
            echo "Структура AstraRegul (первые 3 уровня):"
            find "${ASTRAREGUL_DIR}" -maxdepth 3 -type d 2>&1 | head -30 || echo "Не удалось прочитать"
            echo ""
            echo "Все .exe файлы в AstraRegul:"
            find "${ASTRAREGUL_DIR}" -name "*.exe" -type f 2>&1 | head -20 || echo "Не найдено .exe файлов"
        fi
        echo ""
        echo "Все .exe файлы в drive_c с 'astra' в пути:"
        find "${WINEPREFIX}/drive_c" -name "*.exe" -type f 2>&1 | grep -i astra | head -20 || echo "Не найдено .exe файлов с 'astra' в пути"
    } | tee -a "${LOG_FILE}"
    log_error "Продолжение невозможно без Astra.IDE.exe"
    log_error "Проверьте, что компонент 'astra_ide' был установлен через FSA-AstraInstall"
    exit 1
fi

log_info "Найден Astra.IDE.exe: ${ASTRA_IDE_EXE}"
log_info "Размер файла: $(ls -lh "${ASTRA_IDE_EXE}" | awk '{print $5}')"
log_info "Права доступа: $(ls -l "${ASTRA_IDE_EXE}" | awk '{print $1}')"

# 5. Проверка компонентов Wine
log_info "Проверка компонентов Wine..."
{
    echo "=== WINETRICKS.LOG ==="
    if [ -f "${WINEPREFIX}/winetricks.log" ]; then
        echo "Содержимое winetricks.log:"
        cat "${WINEPREFIX}/winetricks.log"
    else
        echo "winetricks.log не найден"
    fi
    echo ""
    
    echo "=== ПРОВЕРКА DLL ==="
    echo "d3d9.dll:"
    ls -la "${WINEPREFIX}/drive_c/windows/system32/d3d9.dll" 2>&1 || echo "  НЕ НАЙДЕН"
    echo ""
    echo "wpfgfx_v0400.dll:"
    ls -la "${WINEPREFIX}/drive_c/windows/system32/wpfgfx_v0400.dll" 2>&1 || echo "  НЕ НАЙДЕН"
    echo ""
    
    echo "=== РЕЕСТР WINE (настройки D3D9) ==="
    grep -i "d3d9" "${WINEPREFIX}/user.reg" 2>&1 | head -20 || echo "  Настройки D3D9 не найдены"
    echo ""
    grep -i "wpfgfx" "${WINEPREFIX}/user.reg" 2>&1 | head -20 || echo "  Настройки WPF не найдены"
    echo ""
} | tee -a "${LOG_FILE}"

# 6. Проверка существующих логов
log_info "Поиск существующих логов Astra.IDE..."

# Находим реального пользователя Wine
WINE_USER=$(ls -1 "${WINEPREFIX}/drive_c/users/" 2>/dev/null | grep -v "Public" | grep -v "Default" | head -1)
if [ -z "${WINE_USER}" ]; then
    WINE_USER="fsa"  # Fallback
fi
log_info "Найден пользователь Wine: ${WINE_USER}"

{
    echo "=== ЛОГИ УСТАНОВКИ ==="
    # Используем найденный путь к Astra.IDE.exe для поиска SetupCODESYSInst.log
    SETUP_LOG="$(dirname "${ASTRA_IDE_EXE}")/SetupCODESYSInst.log"
    if [ -f "${SETUP_LOG}" ]; then
        echo "Найден SetupCODESYSInst.log:"
        tail -50 "${SETUP_LOG}"
    else
        echo "SetupCODESYSInst.log не найден в: ${SETUP_LOG}"
        # Пробуем альтернативные пути
        ALTERNATIVE_PATHS=(
            "${WINEPREFIX}/drive_c/Program Files/AstraRegul/Astra.IDE_64_1.7.2.1/Astra.IDE/Common/SetupCODESYSInst.log"
            "${WINEPREFIX}/drive_c/Program Files/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common/SetupCODESYSInst.log"
        )
        for alt_path in "${ALTERNATIVE_PATHS[@]}"; do
            for expanded_path in ${alt_path}; do
                if [ -f "${expanded_path}" ]; then
                    echo "Найден SetupCODESYSInst.log в альтернативном пути: ${expanded_path}"
                    tail -50 "${expanded_path}"
                    break 2
                fi
            done
        done
    fi
    echo ""
    
    echo "=== ЛОГИ В TEMP ==="
    TEMP_DIR="${WINEPREFIX}/drive_c/users/${WINE_USER}/AppData/Local/Temp"
    if [ -d "${TEMP_DIR}" ]; then
        echo "Логи в ${TEMP_DIR}:"
        find "${TEMP_DIR}" -name "*.log" -type f -mtime -7 -exec ls -lh {} \; 2>&1 | head -20 || true
    else
        echo "Папка Temp не найдена: ${TEMP_DIR}"
        # Пробуем найти любую папку Temp
        for user_dir in "${WINEPREFIX}/drive_c/users"/*; do
            if [ -d "${user_dir}/AppData/Local/Temp" ]; then
                echo "Найдена альтернативная папка Temp: ${user_dir}/AppData/Local/Temp"
                find "${user_dir}/AppData/Local/Temp" -name "*.log" -type f -mtime -7 -exec ls -lh {} \; 2>&1 | head -20 || true
                break
            fi
        done
    fi
    echo ""
} | tee -a "${LOG_FILE}"

# 7. Настройка детального логирования Wine
log_info "Настройка детального логирования Wine..."
export WINEDEBUG="+d3d9,+wpfgfx,+err,+warn,+fixme-all,+loaddll,+dll"
export WINEDLLOVERRIDES="d3d9=n;wpfgfx=n"

# 8. Запуск Astra.IDE с перехватом вывода
log_info "Запуск Astra.IDE с детальным логированием..."
log_info "Логи Wine будут сохранены в: ${WINE_LOG}"
log_info "Ошибки будут сохранены в: ${ERROR_LOG}"

cd "$(dirname "${ASTRA_IDE_EXE}")"

# Запускаем в фоне с перехватом вывода
{
    echo "=== ЗАПУСК ASTRA.IDE ==="
    echo "Команда: ${WINE_PATH} ${ASTRA_IDE_EXE}"
    echo "WINEPREFIX: ${WINEPREFIX}"
    echo "WINEDEBUG: ${WINEDEBUG}"
    echo "Время запуска: $(date)"
    echo ""
    echo "=== ВЫВОД WINE ==="
    
    # Запускаем с таймаутом 30 секунд (если приложение не запустится)
    timeout 30 "${WINE_PATH}" "${ASTRA_IDE_EXE}" 2>&1 || {
        EXIT_CODE=$?
        echo ""
        echo "=== ПРОЦЕСС ЗАВЕРШИЛСЯ ==="
        echo "Код выхода: ${EXIT_CODE}"
        if [ ${EXIT_CODE} -eq 124 ]; then
            echo "Таймаут 30 секунд истек"
        fi
    }
    
    echo ""
    echo "=== ЗАВЕРШЕНИЕ ==="
    echo "Время завершения: $(date)"
} | tee -a "${LOG_FILE}" | tee -a "${WINE_LOG}" 2>&1

# Фильтруем ошибки в отдельный файл
log_info "Фильтрация ошибок..."
grep -iE "(error|fail|exception|crash|fault|abort|unhandled|0x[0-9a-f]{8})" "${WINE_LOG}" > "${ERROR_LOG}" 2>&1 || {
    echo "Ошибки не найдены в логе" > "${ERROR_LOG}"
}

# 9. Проверка процессов Wine после запуска
log_info "Проверка процессов Wine..."
{
    echo "=== ПРОЦЕССЫ WINE ==="
    ps aux | grep -i wine | grep -v grep || echo "Процессы Wine не найдены"
    echo ""
    
    echo "=== ПРОЦЕССЫ ASTRA.IDE ==="
    ps aux | grep -i "Astra.IDE" | grep -v grep || echo "Процессы Astra.IDE не найдены"
    echo ""
} | tee -a "${LOG_FILE}"

# 10. Создание архива с логами
log_info "Создание архива с логами..."
ARCHIVE_FILE="${LOG_DIR}/astra-ide-diagnostics_${TIMESTAMP}.tar.gz"
tar -czf "${ARCHIVE_FILE}" -C "${LOG_DIR}" \
    "astra-ide-diagnostics_${TIMESTAMP}.log" \
    "wine-debug_${TIMESTAMP}.log" \
    "astra-ide-errors_${TIMESTAMP}.log" 2>&1 | tee -a "${LOG_FILE}"

# 11. Итоговая информация
echo ""
echo "==========================================" | tee -a "${LOG_FILE}"
echo "Диагностика завершена" | tee -a "${LOG_FILE}"
echo "Время завершения: $(date)" | tee -a "${LOG_FILE}"
echo "==========================================" | tee -a "${LOG_FILE}"
echo ""
log_info "════════════════════════════════════════"
log_info "📁 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ"
log_info "════════════════════════════════════════"
log_info ""
log_info "Все логи сохранены в директории:"
log_info "  ${LOG_DIR}"
log_info ""
log_info "Созданные файлы:"
echo "  📄 Полный лог: ${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "  🍷 Лог Wine: ${WINE_LOG}" | tee -a "${LOG_FILE}"
echo "  ❌ Только ошибки: ${ERROR_LOG}" | tee -a "${LOG_FILE}"
echo "  📦 Архив: ${ARCHIVE_FILE}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

# Показываем краткую сводку ошибок
if [ -s "${ERROR_LOG}" ]; then
    log_error "Найдены ошибки! Просмотрите файл: ${ERROR_LOG}"
    echo ""
    echo "=== КРАТКАЯ СВОДКА ОШИБОК (первые 20 строк) ==="
    head -20 "${ERROR_LOG}"
else
    log_info "Ошибок в логах не обнаружено"
fi

echo ""
log_info "Для детального анализа откройте файл: ${LOG_FILE}"