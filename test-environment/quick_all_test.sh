#!/bin/bash
# Быстрый тест всех компонентов (без детального вывода)

echo "=== Быстрый тест всех компонентов ==="
echo "Дата: $(date)"
echo ""

# Создаем лог-файл
LOG_FILE="quick_all_test_$(date +%Y%m%d_%H%M%S).log"
echo "Лог-файл: ${LOG_FILE}"
echo ""

# Создаем тестовый WINEPREFIX
TEST_WINEPREFIX="/tmp/test-wine-quick-$(date +%s)"
TEST_CACHE="/tmp/test-wine-cache-quick-$(date +%s)"

echo "Тестовый WINEPREFIX: ${TEST_WINEPREFIX}" | tee -a "${LOG_FILE}"
echo "Тестовый кэш: ${TEST_CACHE}" | tee -a "${LOG_FILE}"

# Создаем директории
mkdir -p "${TEST_WINEPREFIX}" 2>&1 | tee -a "${LOG_FILE}"
mkdir -p "${TEST_CACHE}" 2>&1 | tee -a "${LOG_FILE}"

# Экспортируем переменные окружения
export WINEPREFIX="${TEST_WINEPREFIX}"
export WINE="wine"
export W_CACHE="${TEST_CACHE}"

echo "Переменные окружения:" | tee -a "${LOG_FILE}"
echo "  WINEPREFIX: ${WINEPREFIX}" | tee -a "${LOG_FILE}"
echo "  WINE: ${WINE}" | tee -a "${LOG_FILE}"
echo "  W_CACHE: ${TEST_CACHE}" | tee -a "${LOG_FILE}"
echo ""

# Проверяем наличие Wine
if ! command -v wine &> /dev/null; then
    echo "❌ Wine не найден! Установите Wine для тестирования." | tee -a "${LOG_FILE}"
    exit 1
fi

WINE_VERSION=$(wine --version 2>&1)
echo "✅ Wine найден: ${WINE_VERSION}" | tee -a "${LOG_FILE}"
echo ""

# Тестируем все компоненты
ALL_COMPONENTS=("dotnet48" "vcrun2013" "vcrun2022" "d3dcompiler_43" "d3dcompiler_47" "dxvk")

echo "=== Быстрый тест компонентов ===" | tee -a "${LOG_FILE}"
echo ""

SUCCESS_COUNT=0
TOTAL_COUNT=${#ALL_COMPONENTS[@]}

for component in "${ALL_COMPONENTS[@]}"; do
    echo -n "Тестируем ${component}... " | tee -a "${LOG_FILE}"
    
    # Запускаем минимальный winetricks с одним компонентом (тихо)
    COMPONENT_OUTPUT=$(./winetricks-minimal "${component}" 2>&1)
    COMPONENT_EXIT_CODE=$?
    
    if [ ${COMPONENT_EXIT_CODE} -eq 0 ]; then
        echo "✅ УСПЕШНО" | tee -a "${LOG_FILE}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ ОШИБКА" | tee -a "${LOG_FILE}"
        echo "   Детали: $(echo "${COMPONENT_OUTPUT}" | tail -3 | tr '\n' ' ')" | tee -a "${LOG_FILE}"
    fi
done

echo "" | tee -a "${LOG_FILE}"
echo "=== РЕЗУЛЬТАТЫ ===" | tee -a "${LOG_FILE}"
echo "Успешно: ${SUCCESS_COUNT}/${TOTAL_COUNT}" | tee -a "${LOG_FILE}"
echo "Процент успеха: $((SUCCESS_COUNT * 100 / TOTAL_COUNT))%" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

if [ ${SUCCESS_COUNT} -eq ${TOTAL_COUNT} ]; then
    echo "🎉 ВСЕ КОМПОНЕНТЫ РАБОТАЮТ! ГОТОВО К ИНТЕГРАЦИИ!" | tee -a "${LOG_FILE}"
elif [ ${SUCCESS_COUNT} -ge 4 ]; then
    echo "✅ Большинство компонентов работают. Можно интегрировать." | tee -a "${LOG_FILE}"
elif [ ${SUCCESS_COUNT} -ge 2 ]; then
    echo "⚠️  Часть компонентов работает. Нужны дополнительные исправления." | tee -a "${LOG_FILE}"
else
    echo "❌ Критические проблемы. Требуется серьезная доработка." | tee -a "${LOG_FILE}"
fi

echo "" | tee -a "${LOG_FILE}"
echo "Лог сохранен в: ${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "Для очистки: rm -rf ${TEST_WINEPREFIX} ${TEST_CACHE}" | tee -a "${LOG_FILE}"
