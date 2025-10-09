#!/bin/bash
# Скрипт для анализа логов тестирования минимального winetricks

echo "=== Анализатор логов тестирования ==="
echo ""

# Находим все лог-файлы
LOG_FILES=$(ls -t *.log 2>/dev/null)

if [ -z "${LOG_FILES}" ]; then
    echo "❌ Лог-файлы не найдены!"
    echo "Сначала запустите тесты:"
    echo "  ./quick_test.sh"
    echo "  ./test_minimal_winetricks.sh"
    exit 1
fi

echo "Найденные лог-файлы:"
for log in ${LOG_FILES}; do
    echo "  - ${log} ($(stat -c %y "${log}" 2>/dev/null || stat -f %Sm "${log}" 2>/dev/null))"
done
echo ""

# Анализируем последний лог
LATEST_LOG=$(echo "${LOG_FILES}" | head -1)
echo "Анализируем: ${LATEST_LOG}"
echo ""

# Извлекаем ключевую информацию
echo "=== Сводка результатов ==="

# Проверяем синтаксис
if grep -q "✅ Синтаксис корректен" "${LATEST_LOG}"; then
    echo "✅ Синтаксис: OK"
else
    echo "❌ Синтаксис: ОШИБКА"
fi

# Проверяем размер
SIZE_INFO=$(grep "Сокращение в" "${LATEST_LOG}" | tail -1)
if [ -n "${SIZE_INFO}" ]; then
    echo "✅ Размер: ${SIZE_INFO}"
else
    echo "❌ Размер: Информация не найдена"
fi

# Проверяем функции
FUNC_COUNT=$(grep "Найдено функций:" "${LATEST_LOG}" | tail -1 | grep -o '[0-9]*')
if [ -n "${FUNC_COUNT}" ]; then
    echo "✅ Функции: ${FUNC_COUNT} найдено"
else
    echo "❌ Функции: Информация не найдена"
fi

# Проверяем компоненты
echo ""
echo "=== Статус компонентов ==="
COMPONENTS=("dotnet48" "vcrun2013" "vcrun2022" "d3dcompiler_43" "d3dcompiler_47" "dxvk")
for comp in "${COMPONENTS[@]}"; do
    if grep -q "✅ ${comp}" "${LATEST_LOG}"; then
        echo "✅ ${comp}: OK"
    else
        echo "❌ ${comp}: ОШИБКА"
    fi
done

# Проверяем зависимости
echo ""
echo "=== Зависимости ==="
if grep -q "✅ Wine найден" "${LATEST_LOG}"; then
    WINE_VERSION=$(grep "✅ Wine найден:" "${LATEST_LOG}" | tail -1)
    echo "✅ ${WINE_VERSION}"
else
    echo "❌ Wine: НЕ НАЙДЕН"
fi

if grep -q "✅ wget найден" "${LATEST_LOG}"; then
    echo "✅ wget: OK"
else
    echo "❌ wget: НЕ НАЙДЕН"
fi

if grep -q "✅ curl найден" "${LATEST_LOG}"; then
    echo "✅ curl: OK"
else
    echo "❌ curl: НЕ НАЙДЕН"
fi

# Проверяем результаты тестирования компонентов
echo ""
echo "=== Результаты тестирования ==="
if grep -q "Тестирование компонента:" "${LATEST_LOG}"; then
    echo "Результаты по компонентам:"
    grep -A 5 "Тестирование компонента:" "${LATEST_LOG}" | grep -E "(✅|❌)" | while read line; do
        echo "  ${line}"
    done
else
    echo "❌ Тестирование компонентов не выполнялось"
fi

# Общая оценка
echo ""
echo "=== Общая оценка ==="
SUCCESS_COUNT=$(grep -c "✅" "${LATEST_LOG}")
ERROR_COUNT=$(grep -c "❌" "${LATEST_LOG}")

echo "Успешных проверок: ${SUCCESS_COUNT}"
echo "Ошибок: ${ERROR_COUNT}"

if [ ${ERROR_COUNT} -eq 0 ]; then
    echo "🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!"
elif [ ${ERROR_COUNT} -lt 3 ]; then
    echo "⚠️  Небольшие проблемы, но в целом OK"
else
    echo "❌ МНОГО ОШИБОК - требуется доработка"
fi

echo ""
echo "Для просмотра полного лога:"
echo "cat ${LATEST_LOG}"
