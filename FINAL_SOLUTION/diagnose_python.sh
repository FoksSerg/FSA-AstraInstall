#!/bin/bash
# Диагностика проблем с Python на Astra Linux

echo "============================================================"
echo "ДИАГНОСТИКА PYTHON НА ASTRA LINUX"
echo "============================================================"

echo "🔍 Информация о системе:"
echo "   📋 Версия Astra Linux: $(cat /etc/astra_version 2>/dev/null || echo 'неизвестно')"
echo "   📋 Версия ядра: $(uname -r)"
echo "   📋 Архитектура: $(uname -m)"

echo ""
echo "🔍 Проверка Python:"
echo "   📋 Python 3: $(python3 --version 2>/dev/null || echo 'не установлен')"
echo "   📋 Python 2: $(python --version 2>/dev/null || echo 'не установлен')"

echo ""
echo "🔍 Проверка репозиториев:"
echo "   📋 Файл sources.list:"
cat /etc/apt/sources.list | head -10

echo ""
echo "🔍 Проверка доступности репозиториев:"
repos=(
    "https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-main/"
    "https://download.astralinux.ru/astra/stable/1.7_x86-64/repository-update/"
)

for repo in "${repos[@]}"; do
    echo "   🔗 Проверяем: $repo"
    if curl -s --head "$repo" | head -n 1 | grep -q "200 OK"; then
        echo "     ✅ Доступен"
    else
        echo "     ❌ Недоступен"
    fi
done

echo ""
echo "🔍 Проверка установленных пакетов Python:"
dpkg -l | grep python | head -10

echo ""
echo "🔍 Проверка Tkinter:"
if python3 -c "import tkinter" 2>/dev/null; then
    echo "   ✅ Tkinter работает"
else
    echo "   ❌ Tkinter не работает"
    echo "   💡 Попробуйте: sudo apt-get install python3-tk"
fi

echo ""
echo "🔍 Проверка pip:"
if pip3 --version 2>/dev/null; then
    echo "   ✅ pip3 работает"
else
    echo "   ❌ pip3 не работает"
    echo "   💡 Попробуйте: sudo apt-get install python3-pip"
fi

echo ""
echo "💡 Рекомендации:"
echo "   1. Если репозитории недоступны - проверьте интернет"
echo "   2. Если Python не установлен - запустите install_python.sh"
echo "   3. Если Tkinter не работает - установите python3-tk"
echo "   4. Если pip не работает - установите python3-pip"
