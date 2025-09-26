#!/bin/bash
# Быстрая установка недостающих компонентов Python

echo "============================================================"
echo "БЫСТРАЯ УСТАНОВКА НЕДОСТАЮЩИХ КОМПОНЕНТОВ PYTHON"
echo "============================================================"

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Требуются права root для установки пакетов"
    echo "Запустите: sudo bash quick_install.sh"
    exit 1
fi

echo "🔍 Проверяем Python 3..."
if python3 --version >/dev/null 2>&1; then
    echo "✅ Python 3 найден: $(python3 --version)"
else
    echo "❌ Python 3 не найден!"
    exit 1
fi

echo ""
echo "🔧 Настраиваем репозитории..."

# Раскомментируем онлайн репозитории
sed -i 's|#deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-main/|deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-main/|g' /etc/apt/sources.list
sed -i 's|#deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-update/|deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-update/|g' /etc/apt/sources.list

echo "   ✅ Репозитории настроены"

echo ""
echo "🔄 Обновляем список пакетов..."
apt-get update

echo ""
echo "📦 Устанавливаем недостающие компоненты..."

# Устанавливаем только то что нужно для GUI
packages=(
    "python3-tk"
    "python3-pip"
)

for package in "${packages[@]}"; do
    echo "   📥 Устанавливаем: $package"
    if apt-get install -y "$package"; then
        echo "     ✅ $package установлен"
    else
        echo "     ❌ $package не установлен"
    fi
done

echo ""
echo "🧪 Проверяем результат..."

echo "   📋 Tkinter:"
if python3 -c "import tkinter; print('✅ Tkinter работает!')" 2>/dev/null; then
    echo "     ✅ Tkinter работает"
else
    echo "     ❌ Tkinter не работает"
fi

echo ""
echo "   📋 pip3:"
if pip3 --version 2>/dev/null; then
    echo "     ✅ pip3 работает"
else
    echo "     ❌ pip3 не работает"
fi

echo ""
echo "🎉 Готово!"
echo ""
echo "💡 Теперь можно запустить основную программу:"
echo "   sudo python3 astra-automation.py"
