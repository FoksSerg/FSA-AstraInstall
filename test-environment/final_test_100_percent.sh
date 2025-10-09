#!/bin/bash
# Финальный тест для достижения 100% успеха

echo "=== ФИНАЛЬНЫЙ ТЕСТ: ЦЕЛЬ 100% УСПЕХА ==="
echo "Дата: $(date)"
echo ""

# Создаем лог-файл
LOG_FILE="final_test_100_percent_$(date +%Y%m%d_%H%M%S).log"
echo "Лог-файл: ${LOG_FILE}"
echo ""

# Создаем тестовый WINEPREFIX
TEST_WINEPREFIX="/tmp/test-wine-final-$(date +%s)"
TEST_CACHE="/tmp/test-wine-cache-final-$(date +%s)"

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

echo "=== ФИНАЛЬНЫЙ ТЕСТ ВСЕХ КОМПОНЕНТОВ ===" | tee -a "${LOG_FILE}"
echo "Цель: 100% успешная установка всех компонентов" | tee -a "${LOG_FILE}"
echo ""

SUCCESS_COUNT=0
TOTAL_COUNT=${#ALL_COMPONENTS[@]}
FAILED_COMPONENTS=()

for component in "${ALL_COMPONENTS[@]}"; do
    echo -n "Тестируем ${component}... " | tee -a "${LOG_FILE}"
    
    # Запускаем минимальный winetricks с одним компонентом
    COMPONENT_OUTPUT=$(./winetricks-minimal "${component}" 2>&1)
    COMPONENT_EXIT_CODE=$?
    
    if [ ${COMPONENT_EXIT_CODE} -eq 0 ]; then
        echo "✅ УСПЕШНО" | tee -a "${LOG_FILE}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ ОШИБКА" | tee -a "${LOG_FILE}"
        FAILED_COMPONENTS+=("${component}")
        echo "   Детали: $(echo "${COMPONENT_OUTPUT}" | tail -3 | tr '\n' ' ')" | tee -a "${LOG_FILE}"
    fi
done

echo "" | tee -a "${LOG_FILE}"
echo "=== РЕЗУЛЬТАТЫ ФИНАЛЬНОГО ТЕСТА ===" | tee -a "${LOG_FILE}"
echo "Успешно: ${SUCCESS_COUNT}/${TOTAL_COUNT}" | tee -a "${LOG_FILE}"
echo "Процент успеха: $((SUCCESS_COUNT * 100 / TOTAL_COUNT))%" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

if [ ${SUCCESS_COUNT} -eq ${TOTAL_COUNT} ]; then
    echo "🎉🎉🎉 100% УСПЕХ! ВСЕ КОМПОНЕНТЫ РАБОТАЮТ! 🎉🎉🎉" | tee -a "${LOG_FILE}"
    echo "✅ ГОТОВО К ИНТЕГРАЦИИ В ОСНОВНОЙ ПРОЕКТ!" | tee -a "${LOG_FILE}"
    echo "" | tee -a "${LOG_FILE}"
    echo "Все компоненты успешно установлены:" | tee -a "${LOG_FILE}"
    for component in "${ALL_COMPONENTS[@]}"; do
        echo "✅ ${component}" | tee -a "${LOG_FILE}"
    done
elif [ ${SUCCESS_COUNT} -ge 4 ]; then
    echo "⚠️  Большинство компонентов работают (${SUCCESS_COUNT}/${TOTAL_COUNT}), но цель 100% не достигнута." | tee -a "${LOG_FILE}"
    echo "❌ Неудачные компоненты:" | tee -a "${LOG_FILE}"
    for component in "${FAILED_COMPONENTS[@]}"; do
        echo "   - ${component}" | tee -a "${LOG_FILE}"
    done
    echo "" | tee -a "${LOG_FILE}"
    echo "🔧 Требуются дополнительные исправления для достижения 100%." | tee -a "${LOG_FILE}"
else
    echo "❌ Критические проблемы. Только ${SUCCESS_COUNT}/${TOTAL_COUNT} компонентов работают." | tee -a "${LOG_FILE}"
    echo "🔧 Требуется серьезная доработка." | tee -a "${LOG_FILE}"
fi

echo "" | tee -a "${LOG_FILE}"
echo "Лог сохранен в: ${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "Для очистки: rm -rf ${TEST_WINEPREFIX} ${TEST_CACHE}" | tee -a "${LOG_FILE}"

# Возвращаем код ошибки если не достигли 100%
if [ ${SUCCESS_COUNT} -ne ${TOTAL_COUNT} ]; then
    exit 1
fi