#!/bin/bash
# -*- coding: utf-8 -*-
# Скрипт для быстрого исправления предупреждений терминала Cursor
# Версия: V3.7.207 (2025.12.29)
# Компания: ООО "НПА Вира-Реалтайм"

echo "=== Исправление предупреждений терминала Cursor ==="
echo ""

# Запускаем Python скрипт для обновления настроек
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/update_cursor_terminal.py"

echo ""
echo "=== Инструкции ==="
echo "1. Перезапустите терминал в Cursor (кнопка 'Relaunch Terminal')"
echo "2. Или полностью перезапустите Cursor"
echo "3. Предупреждение должно исчезнуть"
echo ""

