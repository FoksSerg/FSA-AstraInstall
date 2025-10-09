#!/bin/bash
# Полный тест всех компонентов минимального winetricks

echo "=== Полный тест всех компонентов минимального winetricks ==="
echo "Дата: $(date)"
echo ""

# Создаем лог-файл
LOG_FILE="full_test_all_components_$(date +%Y%m%d_%H%M%S).log"
echo "Лог-файл: ${LOG_FILE}"
echo ""

echo "=== Полный тест всех компонентов ===" | tee -a "${LOG_FILE}"
echo "Дата: $(date)" | tee -a "${LOG_FILE}"
echo "Система: $(uname -a)" | tee -a "${LOG_FILE}"
echo "Пользователь: $(whoami)" | tee -a "${LOG_FILE}"
echo ""

# Создаем тестовый WINEPREFIX
TEST_WINEPREFIX="/tmp/test-wine-full-$(date +%s)"
TEST_CACHE="/tmp/test-wine-cache-full-$(date +%s)"

echo "Тестовый WINEPREFIX: ${TEST_WINEPREFIX}" | tee -a "${LOG_FILE}"
echo "Тестовый кэш: ${TEST_CACHE}" | tee -a "${LOG_FILE}"
echo ""

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

# Тестируем все компоненты по отдельности
ALL_COMPONENTS=("dotnet48" "vcrun2013" "vcrun2022" "d3dcompiler_43" "d3dcompiler_47" "dxvk")

echo "=== Тестирование компонентов по отдельности ===" | tee -a "${LOG_FILE}"
echo ""

SUCCESS_COUNT=0
TOTAL_COUNT=${#ALL_COMPONENTS[@]}

for component in "${ALL_COMPONENTS[@]}"; do
    echo "--- Тестирование компонента: ${component} ---" | tee -a "${LOG_FILE}"
    echo "Время начала: $(date)" | tee -a "${LOG_FILE}"
    
    # Запускаем минимальный winetricks с одним компонентом
    COMPONENT_OUTPUT=$(./winetricks-minimal "${component}" 2>&1)
    COMPONENT_EXIT_CODE=$?
    
    echo "Код возврата: ${COMPONENT_EXIT_CODE}" | tee -a "${LOG_FILE}"
    echo "Вывод:" | tee -a "${LOG_FILE}"
    echo "${COMPONENT_OUTPUT}" | tee -a "${LOG_FILE}"
    
    if [ ${COMPONENT_EXIT_CODE} -eq 0 ]; then
        echo "✅ ${component} - УСПЕШНО" | tee -a "${LOG_FILE}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ ${component} - ОШИБКА" | tee -a "${LOG_FILE}"
        
        # Анализируем ошибки
        if echo "${COMPONENT_OUTPUT}" | grep -q "Нет такого файла или каталога"; then
            echo "   🔍 Проблема: Директория не создана" | tee -a "${LOG_FILE}"
        elif echo "${COMPONENT_OUTPUT}" | grep -q "/dev/null"; then
            echo "   🔍 Проблема: Попытка копирования в /dev/null" | tee -a "${LOG_FILE}"
        elif echo "${COMPONENT_OUTPUT}" | grep -q "Command failed"; then
            echo "   🔍 Проблема: Команда не выполнена" | tee -a "${LOG_FILE}"
        else
            echo "   🔍 Проблема: Другая ошибка" | tee -a "${LOG_FILE}"
        fi
    fi
    
    echo "Время завершения: $(date)" | tee -a "${LOG_FILE}"
    echo "" | tee -a "${LOG_FILE}"
done

echo "=== Результаты тестирования по отдельности ===" | tee -a "${LOG_FILE}"
echo "Успешно: ${SUCCESS_COUNT}/${TOTAL_COUNT}" | tee -a "${LOG_FILE}"
echo "Процент успеха: $((SUCCESS_COUNT * 100 / TOTAL_COUNT))%" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

# Тестируем установку всех компонентов сразу
echo "=== Тестирование установки всех компонентов сразу ===" | tee -a "${LOG_FILE}"
echo "Время начала: $(date)" | tee -a "${LOG_FILE}"

ALL_COMPONENTS_OUTPUT=$(./winetricks-minimal "${ALL_COMPONENTS[@]}" 2>&1)
ALL_COMPONENTS_EXIT_CODE=$?

echo "Код возврата: ${ALL_COMPONENTS_EXIT_CODE}" | tee -a "${LOG_FILE}"
echo "Вывод:" | tee -a "${LOG_FILE}"
echo "${ALL_COMPONENTS_OUTPUT}" | tee -a "${LOG_FILE}"

if [ ${ALL_COMPONENTS_EXIT_CODE} -eq 0 ]; then
    echo "✅ Все компоненты установлены успешно" | tee -a "${LOG_FILE}"
else
    echo "❌ Ошибка при установке всех компонентов" | tee -a "${LOG_FILE}"
fi

echo "Время завершения: $(date)" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

# Итоговая сводка
echo "=== ИТОГОВАЯ СВОДКА ===" | tee -a "${LOG_FILE}"
echo "Дата: $(date)" | tee -a "${LOG_FILE}"
echo "Система: $(uname -a)" | tee -a "${LOG_FILE}"
echo "Wine: ${WINE_VERSION}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"
echo "Результаты по компонентам:" | tee -a "${LOG_FILE}"
for component in "${ALL_COMPONENTS[@]}"; do
    if grep -q "✅ ${component} - УСПЕШНО" "${LOG_FILE}"; then
        echo "✅ ${component}" | tee -a "${LOG_FILE}"
    else
        echo "❌ ${component}" | tee -a "${LOG_FILE}"
    fi
done
echo "" | tee -a "${LOG_FILE}"
echo "Общий результат: ${SUCCESS_COUNT}/${TOTAL_COUNT} компонентов работают" | tee -a "${LOG_FILE}"
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
echo "=== Информация для очистки ===" | tee -a "${LOG_FILE}"
echo "Тестовый WINEPREFIX: ${TEST_WINEPREFIX}" | tee -a "${LOG_FILE}"
echo "Тестовый кэш: ${TEST_CACHE}" | tee -a "${LOG_FILE}"
echo "Лог сохранен в: ${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"
echo "Для очистки тестовых файлов выполните:" | tee -a "${LOG_FILE}"
echo "rm -rf ${TEST_WINEPREFIX} ${TEST_CACHE}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"
echo "Для анализа лога:" | tee -a "${LOG_FILE}"
echo "cat ${LOG_FILE}" | tee -a "${LOG_FILE}"
