#!/bin/bash
# ИТОГОВОЕ РЕШЕНИЕ: Установка Python на Astra Linux

echo "============================================================"
echo "ИТОГОВОЕ РЕШЕНИЕ: УСТАНОВКА PYTHON НА ASTRA LINUX"
echo "============================================================"

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Требуются права root для установки пакетов"
    echo "Запустите: sudo bash install_python.sh"
    exit 1
fi

echo "🔍 Проверяем текущее состояние системы..."

# Проверяем версию Astra Linux
if [ -f /etc/astra_version ]; then
    echo "   📋 Версия Astra Linux: $(cat /etc/astra_version)"
else
    echo "   ⚠️ Не удалось определить версию Astra Linux"
fi

# Проверяем Python
python3 --version 2>/dev/null && echo "   ✅ Python 3 найден" || echo "   ❌ Python 3 не найден"
python --version 2>/dev/null && echo "   ✅ Python 2 найден" || echo "   ❌ Python 2 не найден"

# Проверяем нужно ли устанавливать Python 3
if ! python3 --version >/dev/null 2>&1; then
    echo "   ❌ Python 3 не найден, устанавливаем..."
    PYTHON3_NEEDED=true
else
    echo "   ✅ Python 3 уже установлен, проверяем компоненты..."
    PYTHON3_NEEDED=false
fi

echo ""
echo "🔧 Настраиваем репозитории Astra Linux..."

# Создаем резервную копию sources.list
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

echo ""
echo "🔍 Ищем доступные версии Python..."

# Ищем все доступные версии Python
echo "   📋 Доступные пакеты Python:"
apt-cache search python3 | grep -E "python3[0-9]" | head -10

echo ""
echo "📦 Устанавливаем Python компоненты..."

if [ "$PYTHON3_NEEDED" = true ]; then
    echo "   📥 Устанавливаем Python 3..."
    if apt-get install -y python3; then
        echo "     ✅ Python 3 установлен"
    else
        echo "     ❌ Ошибка установки Python 3"
    fi
else
    echo "   ✅ Python 3 уже установлен, пропускаем"
fi

# Устанавливаем дополнительные компоненты
echo ""
echo "📦 Устанавливаем дополнительные компоненты..."

components=(
    "python3-dev"
    "python3-pip" 
    "python3-setuptools"
    "python3-distutils"
    "python3-tk"
    "python3-venv"
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
python --version 2>/dev/null || echo "     ❌ Python 2 не работает"

echo ""
echo "   📋 Проверка Tkinter:"
if python3 -c "import tkinter; print('✅ Tkinter работает!')" 2>/dev/null; then
    echo "     ✅ Tkinter установлен и работает"
else
    echo "     ❌ Tkinter не работает"
    echo "     💡 Попробуйте установить: apt-get install python3-tk"
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
echo "💡 Дополнительные команды:"
echo "   • Проверить Python: python3 --version"
echo "   • Проверить Tkinter: python3 -c 'import tkinter; print("OK")'"
echo "   • Установить пакет: pip3 install package_name"
echo "   • Создать виртуальное окружение: python3 -m venv myenv"

echo ""
echo "📋 Если что-то не работает:"
echo "   1. Проверьте интернет соединение"
echo "   2. Попробуйте: apt-get update && apt-get install -f"
echo "   3. Проверьте доступность репозиториев"
echo "   4. Обратитесь к администратору системы"
