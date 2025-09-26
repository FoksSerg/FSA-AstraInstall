#!/bin/bash
# ГЛАВНЫЙ СКРИПТ: Автоматическая установка и запуск GUI

echo "============================================================"
echo "ASTRA AUTOMATION - АВТОМАТИЧЕСКАЯ УСТАНОВКА И ЗАПУСК"
echo "============================================================"

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Требуются права root для установки пакетов"
    echo "Запустите: sudo bash astra_install.sh"
    exit 1
fi

echo "🔍 Проверяем систему..."

# Проверяем версию Astra Linux
if [ -f /etc/astra_version ]; then
    echo "   📋 Версия Astra Linux: $(cat /etc/astra_version)"
else
    echo "   ⚠️ Не удалось определить версию Astra Linux"
fi

# Проверяем Python
echo "   📋 Python 3: $(python3 --version 2>/dev/null || echo 'не найден')"
echo "   📋 Python 2: $(python --version 2>/dev/null || echo 'не найден')"

echo ""
echo "🔧 Проверяем компоненты для GUI..."

# Проверяем что нужно для GUI
NEED_TKINTER=false
NEED_PIP=false
NEED_PYTHON3=false

# Проверяем Python 3
if ! python3 --version >/dev/null 2>&1; then
    echo "   ❌ Python 3 не найден"
    NEED_PYTHON3=true
else
    echo "   ✅ Python 3 найден"
fi

# Проверяем Tkinter
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "   ❌ Tkinter не найден"
    NEED_TKINTER=true
else
    echo "   ✅ Tkinter найден"
fi

# Проверяем pip3
if ! pip3 --version >/dev/null 2>&1; then
    echo "   ❌ pip3 не найден"
    NEED_PIP=true
else
    echo "   ✅ pip3 найден"
fi

# Если все готово - запускаем GUI
if [ "$NEED_PYTHON3" = false ] && [ "$NEED_TKINTER" = false ] && [ "$NEED_PIP" = false ]; then
    echo ""
    echo "🎉 Все компоненты готовы!"
    echo "🚀 Запускаем графический интерфейс..."
    echo ""
    
    # Запускаем основную программу
    python3 astra-automation.py
    exit 0
fi

echo ""
echo "📦 Устанавливаем недостающие компоненты..."

# Настраиваем репозитории
echo "   🔧 Настраиваем репозитории..."
cp /etc/apt/sources.list /etc/apt/sources.list.backup

# Добавляем официальные репозитории Astra Linux
cat > /etc/apt/sources.list << 'EOF'
# Официальные репозитории Astra Linux
deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-main/ 1.7_x86-64 main contrib non-free
deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-update/ 1.7_x86-64 main contrib non-free
deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-base/ 1.7_x86-64 main contrib non-free
deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-extended/ 1.7_x86-64 main contrib non-free

# Отключаем DVD репозитории
# deb cdrom:[Astra Linux 1.7 x86-64]/ 1.7_x86-64 main contrib non-free
EOF

echo "   ✅ Репозитории настроены"

echo ""
echo "🔄 Обновляем список пакетов..."
apt-get update

# Устанавливаем недостающие компоненты
if [ "$NEED_PYTHON3" = true ]; then
    echo "   📥 Устанавливаем Python 3..."
    apt-get install -y python3
fi

if [ "$NEED_TKINTER" = true ]; then
    echo "   📥 Устанавливаем Tkinter..."
    if apt-get install -y python3-tk; then
        echo "     ✅ python3-tk установлен"
    else
        echo "     ❌ Не удалось установить python3-tk"
    fi
fi

if [ "$NEED_PIP" = true ]; then
    echo "   📥 Устанавливаем pip3..."
    if apt-get install -y python3-pip; then
        echo "     ✅ python3-pip установлен"
    else
        echo "     ❌ Не удалось установить python3-pip"
    fi
fi

echo ""
echo "🔧 Исправляем зависимости..."
apt-get install -f -y

echo ""
echo "🧪 Проверяем результат..."

# Финальная проверка
echo "   📋 Python 3: $(python3 --version 2>/dev/null || echo 'не работает')"
echo "   📋 Tkinter: $(python3 -c 'import tkinter; print("работает")' 2>/dev/null || echo 'не работает')"
echo "   📋 pip3: $(pip3 --version 2>/dev/null || echo 'не работает')"

echo ""
echo "🎉 Установка завершена!"
echo "🚀 Запускаем графический интерфейс..."

# Проверяем какая версия Python доступна
if python3 --version >/dev/null 2>&1; then
    echo "   📋 Используем Python 3: $(python3 --version)"
    python3 astra-automation.py
elif python --version >/dev/null 2>&1; then
    echo "   📋 Используем Python 2: $(python --version)"
    python astra-automation.py
else
    echo "   ❌ Python не найден!"
    exit 1
fi
