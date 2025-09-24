#!/bin/bash

echo "=================================================="
echo "Auto Setup for Astra Linux 1.7 (Clean Install)"
echo "=================================================="

# Функция для запроса подтверждения
confirm_action() {
    read -p "$1 (y/N): " response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Функция для проверки команд
check_cmd() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "⚠ $1 (продолжаем...)"
    fi
}

# 1. Создаем backup репозиториев
echo "1. Создание backup репозиториев..."
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup
echo "✅ Backup создан: /etc/apt/sources.list.backup"

# 2. Проверка всех репозиториев
echo ""
echo "2. Проверка репозиториев..."
echo "=========================="

# Временный файл для нового sources.list
TEMP_FILE=$(mktemp)
echo "# Astra Linux repositories - auto configured" > "$TEMP_FILE"

# Счетчики
ACTIVATED_COUNT=0
DEACTIVATED_COUNT=0

# Функция проверки одного репозитория
check_single_repo() {
    local repo_line="$1"
    local test_file=$(mktemp)
    echo "$repo_line" > "$test_file"

    if sudo apt-get update -o Dir::Etc::sourcelist="$test_file" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" &>/dev/null; then
        echo "✅ Рабочий: $(echo "$repo_line" | awk '{print $2}')"
        rm -f "$test_file"
        return 0
    else
        echo "❌ Не доступен: $(echo "$repo_line" | awk '{print $2}')"
        rm -f "$test_file"
        return 1
    fi
}

# Обрабатываем все репозитории (исправленная логика)
while IFS= read -r line; do
    if [[ "$line" =~ ^#?deb ]]; then
        if [[ "$line" == \#* ]]; then
            # Закомментированный репозиторий - проверяем и решаем активировать или оставить как есть
            clean_line="${line#\#}"
            clean_line="$(echo "$clean_line" | sed 's/^[[:space:]]*//')"
            if check_single_repo "$clean_line"; then
                echo "$clean_line" >> "$TEMP_FILE"
                ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
            else
                echo "$line" >> "$TEMP_FILE"
                DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
            fi
        else
            # Активный репозиторий - проверяем и решаем оставить активным или закомментировать
            if check_single_repo "$line"; then
                echo "$line" >> "$TEMP_FILE"
                ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
            else
                echo "# $line" >> "$TEMP_FILE"
                DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
            fi
        fi
    else
        # Все остальные строки (комментарии, пустые строки) - просто копируем
        echo "$line" >> "$TEMP_FILE"
    fi
done < /etc/apt/sources.list

# Удаляем дубликаты из временного файла
UNIQUE_TEMP_FILE=$(mktemp)
awk '!seen[$0]++' "$TEMP_FILE" > "$UNIQUE_TEMP_FILE"
mv "$UNIQUE_TEMP_FILE" "$TEMP_FILE"

# 3. Анализ системы для статистики
echo ""
echo "3. Анализ системы..."
echo "==================="

# Сохраняем временный файл для дальнейшего использования
TEMP_BACKUP="/tmp/apt_sources_final.tmp"
cp "$TEMP_FILE" "$TEMP_BACKUP"

# Временно применяем изменения для анализа
sudo cp "$TEMP_BACKUP" /etc/apt/sources.list

# Обновляем список пакетов
sudo apt-get update >/dev/null 2>&1

# Анализируем обновления
UPDATABLE_PACKAGES=$(apt list --upgradable 2>/dev/null | wc -l)
PACKAGES_TO_UPDATE=$((UPDATABLE_PACKAGES - 1))

# Анализируем автоудаление
AUTOREMOVE_INFO=$(sudo apt-get autoremove --simulate 2>/dev/null)
PACKAGES_TO_REMOVE=$(echo "$AUTOREMOVE_INFO" | grep -oP '\d+ пакетов? будет удалено' | grep -oP '\d+' || echo "0")
if [ -z "$PACKAGES_TO_REMOVE" ]; then
    PACKAGES_TO_REMOVE=0
fi

# Восстанавливаем оригинальный файл пока не подтвердили
sudo cp /etc/apt/sources.list.backup /etc/apt/sources.list

# 4. Показываем статистику
echo ""
echo "СТАТИСТИКА ОПЕРАЦИЙ:"
echo "===================="
echo "📡 Репозитории:"
echo "   • Активировано: $ACTIVATED_COUNT рабочих"
echo "   • Деактивировано: $DEACTIVATED_COUNT нерабочих"

echo ""
echo "📦 Обновление системы:"
echo "   • Пакетов для обновления: $PACKAGES_TO_UPDATE"
if [ $PACKAGES_TO_UPDATE -gt 0 ]; then
    echo "   • Первые пакеты:"
    sudo cp "$TEMP_BACKUP" /etc/apt/sources.list
    sudo apt-get update >/dev/null 2>&1
    apt list --upgradable 2>/dev/null | head -6 | tail -5 | sed 's/^/     - /'
    sudo cp /etc/apt/sources.list.backup /etc/apt/sources.list
fi

echo ""
echo "🗑️  Очистка системы:"
echo "   • Пакетов для удаления: $PACKAGES_TO_REMOVE"

echo ""
echo "📦 Установка новых пакетов:"
echo "   • Python и зависимости: 4 пакета"
echo "   • Системные утилиты: 5 пакетов"
echo "   • Wine и компоненты: 3-5 пакетов"
echo "   • ИТОГО: 12-14 пакетов"

# 5. Запрос подтверждения
echo ""
echo "=================================================="
if ! confirm_action "Выполнить все операции?"; then
    echo "❌ Операция отменена пользователем"
    rm -f "$TEMP_FILE" "$TEMP_BACKUP"
    exit 0
fi

# 6. Применяем изменения с репозиториями
echo ""
echo "4. Применение изменений..."
echo "=========================="
sudo cp "$TEMP_BACKUP" /etc/apt/sources.list

echo "Активированные репозитории:"
grep "^deb" /etc/apt/sources.list | sed 's/^/   • /'

# 7. Обновление системы
echo ""
echo "5. Обновление системы..."
echo "========================"

echo "Обновление списка пакетов..."
sudo apt-get update
check_cmd "Список пакетов обновлен"

if [ $PACKAGES_TO_UPDATE -gt 0 ]; then
    echo "Обновление $PACKAGES_TO_UPDATE пакетов..."
    sudo apt-get dist-upgrade -y
    check_cmd "Система обновлена"
else
    echo "✅ Нет пакетов для обновления"
fi

if [ "$PACKAGES_TO_REMOVE" -gt 0 ]; then
    echo "Удаление $PACKAGES_TO_REMOVE ненужных пакетов..."
    sudo apt-get autoremove -y
    check_cmd "Ненужные пакеты удалены"
else
    echo "✅ Нет пакетов для удаления"
fi

# 8. Установка пакетов
echo ""
echo "6. Установка новых пакетов..."
echo "============================="

# Python
echo "Установка Python и зависимостей..."
PYTHON_PACKAGES="python3 python3-pip python3-apt python3-venv"
sudo apt-get install -y $PYTHON_PACKAGES
check_cmd "Python установлен"

# Системные утилиты
echo "Установка системных утилит..."
UTILITY_PACKAGES="wget curl git nano htop"
sudo apt-get install -y $UTILITY_PACKAGES
check_cmd "Системные утилиты установлены"

# Wine
echo "Установка Wine..."
if apt-cache show wine >/dev/null 2>&1; then
    WINE_PACKAGES="wine"
    sudo apt-get install -y $WINE_PACKAGES
    check_cmd "Wine установлен"
else
    WINE_PACKAGES="wine64 wine32"
    sudo apt-get install -y $WINE_PACKAGES
    check_cmd "Wine64/Wine32 установлены"
fi

# Winetricks и зависимости
WINE_DEPS="winetricks libgl1-mesa-dri libgl1-mesa-glx"
sudo apt-get install -y $WINE_DEPS
check_cmd "Компоненты Wine установлены"

# 9. Финальные настройки
echo ""
echo "7. Финальные настройки..."
echo "========================="

CURRENT_USER=$(logname 2>/dev/null || echo "$SUDO_USER" || echo "$USER")
if [ -n "$CURRENT_USER" ] && [ "$CURRENT_USER" != "root" ]; then
    echo "Настройка Wine для пользователя: $CURRENT_USER"
    sudo -u "$CURRENT_USER" winecfg &>/dev/null &
    echo "✅ Настройка Wine запущена в фоне"
else
    echo "⚠ Запустите 'winecfg' после завершения от имени пользователя"
fi

# Очистка временных файлов
rm -f "$TEMP_FILE" "$TEMP_BACKUP"

echo ""
echo "=================================================="
echo "УСТАНОВКА УСПЕШНО ЗАВЕРШЕНА!"
echo "=================================================="
