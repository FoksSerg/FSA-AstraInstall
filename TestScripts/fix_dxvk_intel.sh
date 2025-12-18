#!/bin/bash
# -*- coding: utf-8 -*-
#
# Скрипт исправления проблемы DXVK на Intel HD Graphics
# Отключает DXVK и использует встроенный d3d9 Wine
# Версия: 1.0
# Компания: ООО "НПА Вира-Реалтайм"
#

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Исправление проблемы DXVK на Intel HD Graphics"
echo "Версия скрипта: 1.0"
echo "Время запуска: $(date)"
echo "=========================================="
echo ""

# Функция для логирования
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 1. Поиск WINEPREFIX
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

# 2. Проверка наличия DXVK DLL
SYSTEM32_DIR="${WINEPREFIX}/drive_c/windows/system32"
DXVK_DLLS=(
    "d3d9.dll"
    "d3d10.dll"
    "d3d10_1.dll"
    "d3d10core.dll"
    "d3d11.dll"
    "dxgi.dll"
)

log_info "Проверка наличия DXVK DLL..."
DXVK_FOUND=false
for dll in "${DXVK_DLLS[@]}"; do
    DLL_PATH="${SYSTEM32_DIR}/${dll}"
    if [ -f "${DLL_PATH}" ]; then
        # Проверяем, что это DXVK (обычно больше 1MB)
        SIZE=$(stat -f%z "${DLL_PATH}" 2>/dev/null || stat -c%s "${DLL_PATH}" 2>/dev/null)
        if [ "${SIZE}" -gt 1048576 ]; then
            log_warn "Найден DXVK DLL: ${dll} (размер: $(numfmt --to=iec-i --suffix=B ${SIZE} 2>/dev/null || echo "${SIZE} bytes"))"
            DXVK_FOUND=true
        fi
    fi
done

if [ "${DXVK_FOUND}" = false ]; then
    log_info "DXVK DLL не найдены. Проблема может быть в другом."
    log_info "Проверяем настройки реестра..."
fi

# 3. Создание резервной копии
BACKUP_DIR="${WINEPREFIX}/dxvk_backup_$(date +%Y%m%d_%H%M%S)"
log_info "Создание резервной копии в: ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"

# 4. Удаление/переименование DXVK DLL
log_info "Отключение DXVK..."
DLLS_REMOVED=0
for dll in "${DXVK_DLLS[@]}"; do
    DLL_PATH="${SYSTEM32_DIR}/${dll}"
    if [ -f "${DLL_PATH}" ]; then
        SIZE=$(stat -f%z "${DLL_PATH}" 2>/dev/null || stat -c%s "${DLL_PATH}" 2>/dev/null)
        if [ "${SIZE}" -gt 1048576 ]; then
            log_info "  Резервная копия: ${dll}"
            cp "${DLL_PATH}" "${BACKUP_DIR}/${dll}"
            log_info "  Переименование: ${dll} -> ${dll}.dxvk_disabled"
            mv "${DLL_PATH}" "${DLL_PATH}.dxvk_disabled"
            DLLS_REMOVED=$((DLLS_REMOVED + 1))
        fi
    fi
done

if [ ${DLLS_REMOVED} -eq 0 ]; then
    log_warn "DXVK DLL не найдены для отключения"
else
    log_info "Отключено DXVK DLL: ${DLLS_REMOVED} файлов"
fi

# 5. Проверка и очистка реестра от DXVK настроек
log_info "Проверка реестра Wine..."
USER_REG="${WINEPREFIX}/user.reg"
if [ -f "${USER_REG}" ]; then
    # Проверяем наличие настроек DXVK в реестре
    if grep -qi "dxvk" "${USER_REG}" 2>/dev/null; then
        log_warn "Найдены настройки DXVK в реестре"
        log_info "Создание резервной копии реестра..."
        cp "${USER_REG}" "${BACKUP_DIR}/user.reg.backup"
        log_info "Рекомендуется проверить реестр вручную на наличие настроек DXVK"
    else
        log_info "Настройки DXVK в реестре не найдены"
    fi
fi

# 6. Проверка DLL overrides
log_info "Проверка DLL overrides..."
if grep -qi "d3d9.*native\|d3d11.*native\|dxgi.*native" "${USER_REG}" 2>/dev/null; then
    log_warn "Найдены DLL overrides для DXVK в реестре"
    log_info "Создание резервной копии реестра..."
    cp "${USER_REG}" "${BACKUP_DIR}/user.reg.backup"
    log_info "Рекомендуется удалить DLL overrides для d3d9, d3d11, dxgi"
    log_info "Можно использовать: winecfg -> Libraries -> удалить d3d9, d3d11, dxgi"
else
    log_info "DLL overrides для DXVK не найдены"
fi

# 7. Проверка winetricks.log
log_info "Проверка winetricks.log..."
WINETRICKS_LOG="${WINEPREFIX}/winetricks.log"
if [ -f "${WINETRICKS_LOG}" ]; then
    if grep -qi "dxvk" "${WINETRICKS_LOG}" 2>/dev/null; then
        log_warn "DXVK установлен через winetricks"
        log_info "Для полного удаления можно использовать: winetricks --uninstall dxvk"
    else
        log_info "DXVK не установлен через winetricks"
    fi
fi

# 8. Итоговая информация
echo ""
echo "=========================================="
echo "Исправление завершено"
echo "Время завершения: $(date)"
echo "=========================================="
echo ""

if [ ${DLLS_REMOVED} -gt 0 ]; then
    log_info "✅ DXVK отключен"
    log_info "   Отключено DLL: ${DLLS_REMOVED}"
    log_info "   Резервная копия: ${BACKUP_DIR}"
    echo ""
    log_info "Теперь Wine будет использовать встроенный d3d9 вместо DXVK"
    log_info "Попробуйте запустить Astra.IDE снова"
    echo ""
    log_warn "Если проблема сохранится:"
    log_warn "  1. Проверьте DLL overrides в winecfg"
    log_warn "  2. Убедитесь, что нет других настроек DXVK"
    log_warn "  3. Восстановите из резервной копии: ${BACKUP_DIR}"
else
    log_warn "DXVK DLL не найдены"
    log_info "Возможно, проблема в другом месте:"
    log_info "  1. Проверьте настройки реестра Wine"
    log_info "  2. Проверьте DLL overrides в winecfg"
    log_info "  3. Проверьте версию Wine и драйверы видеокарты"
fi

echo ""
log_info "Для восстановления DXVK:"
echo "  cp ${BACKUP_DIR}/*.dll ${SYSTEM32_DIR}/"
echo ""

