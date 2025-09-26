#!/bin/bash
# Обновленный скрипт установки недостающих компонентов Python

echo "============================================================"
echo "УСТАНОВКА НЕДОСТАЮЩИХ КОМПОНЕНТОВ PYTHON"
echo "============================================================"

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Требуются права root для установки пакетов"
    echo "Запустите: sudo bash install_python_components.sh"
    exit 1
fi

echo "🔍 Проверяем текущее состояние Python..."
python3 --version 2>/dev/null && echo "✅ Python 3 найден" || echo "❌ Python 3 не найден"

echo ""
echo "🔧 Настраиваем репозитории Astra Linux..."

# Создаем резервную копию sources.list
cp /etc/apt/sources.list /etc/apt/sources.list.backup

# Добавляем онлайн репозитории (раскомментируем)
sed -i 's|#deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-main/|deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-main/|g' /etc/apt/sources.list
sed -i 's|#deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-update/|deb https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-update/|g' /etc/apt/sources.list

echo "   ✅ Репозитории настроены"

echo ""
echo "🔄 Обновляем список пакетов..."
apt-get update

echo ""
echo "📦 Устанавливаем недостающие компоненты Python..."

# Устанавливаем только недостающие компоненты
components=(
    "python3-tk"
    "python3-pip"
    "python3-dev"
    "python3-setuptools"
    "python3-distutils"
)

for component in "${components[@]}"; do
    echo "   📥 Устанавливаем: $component"
    if apt-get install -y "$component"; then
        echo "     ✅ $component установлен"
    else
        echo "     ⚠️ $component не установлен (возможно недоступен)"
    fi
done

echo ""
echo "🔧 Исправляем зависимости..."
apt-get install -f -y

echo ""
echo "🧪 Проверяем установку..."

echo "   📋 Версии Python:"
python3 --version 2>/dev/null || echo "     ❌ Python 3 не работает"

echo ""
echo "   📋 Проверка Tkinter:"
if python3 -c "import tkinter; print('✅ Tkinter работает!')" 2>/dev/null; then
    echo "     ✅ Tkinter установлен и работает"
else
    echo "     ❌ Tkinter не работает"
fi

echo ""
echo "   📋 Проверка pip:"
if pip3 --version 2>/dev/null; then
    echo "     ✅ pip3 работает"
else
    echo "     ❌ pip3 не работает"
fi

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "💡 Теперь можно запустить основную программу:"
echo "   sudo python3 astra-automation.py"

echo ""
echo "📋 Дополнительная информация:"
echo "   • Python 3: $(python3 --version)"
echo "   • pip3: $(pip3 --version 2>/dev/null || echo 'не установлен')"
echo "   • Tkinter: $(python3 -c 'import tkinter; print("работает")' 2>/dev/null || echo 'не работает')"
