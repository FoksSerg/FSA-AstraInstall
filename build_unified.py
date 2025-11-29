#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт объединения astra_update.sh + astra_install.sh + astra_automation.py
в единый Python файл FSA-AstraInstall_unified.py

Версия: V2.6.138 (2025.11.16)
Компания: ООО "НПА Вира-Реалтайм"
"""

import os
import sys
import re
from pathlib import Path

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
BUILD_DIR = SCRIPT_DIR / "build"
OUTPUT_FILE = BUILD_DIR / "FSA-AstraInstall_unified.py"

# Исходные файлы
ASTRA_UPDATE_SH = SCRIPT_DIR / "astra_update.sh"
ASTRA_INSTALL_SH = SCRIPT_DIR / "astra_install.sh"
ASTRA_AUTOMATION_PY = SCRIPT_DIR / "astra_automation.py"

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def print_step(message):
    print(f"\n[#] {message}")

def print_success(message):
    print(f"[OK] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def read_file_safe(filepath):
    """Безопасное чтение файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print_error(f"Не удалось прочитать {filepath}: {e}")
        sys.exit(1)

# ============================================================================
# КОНВЕРТАЦИЯ BASH В PYTHON
# ============================================================================

def convert_bash_to_python(bash_code, script_name):
    """Конвертирует bash скрипт в Python код"""
    
    # Удаляем shebang и комментарии версии (они будут в начале объединенного файла)
    lines = bash_code.split('\n')
    result_lines = []
    skip_shebang = True
    
    for line in lines:
        # Пропускаем shebang
        if skip_shebang and (line.startswith('#!') or line.strip() == ''):
            continue
        skip_shebang = False
        
        # Пропускаем пустые строки в начале
        if not result_lines and line.strip() == '':
            continue
        
        # Конвертируем основные конструкции
        converted = convert_bash_line(line, script_name)
        if converted:
            result_lines.append(converted)
    
    return '\n'.join(result_lines)

def convert_bash_line(line, script_name):
    """Конвертирует одну строку bash в Python"""
    
    stripped = line.strip()
    
    # Пропускаем комментарии (кроме важных)
    if stripped.startswith('#') and not any(marker in stripped for marker in ['КРИТИЧНО', 'ВАЖНО', 'TODO']):
        return None
    
    # Конвертируем переменные окружения
    if re.match(r'^[A-Z_]+=".*"$', stripped):
        var_name = stripped.split('=')[0]
        var_value = stripped.split('=', 1)[1].strip('"')
        return f'    {var_name} = "{var_value}"'
    
    # Конвертируем функции (упрощенно)
    if stripped.startswith('function ') or re.match(r'^\w+\(\)\s*\{?$', stripped):
        func_name = re.search(r'(\w+)', stripped).group(1)
        return f'def {func_name}():'
    
    # Конвертируем echo в print
    if stripped.startswith('echo '):
        content = stripped[5:].strip()
        # Убираем кавычки если есть
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        return f'    print("{content}")'
    
    # Конвертируем log_message
    if 'log_message' in stripped:
        # Извлекаем сообщение
        match = re.search(r'log_message\s+"([^"]+)"', stripped)
        if match:
            msg = match.group(1)
            return f'    log_message("{msg}")'
    
    # Конвертируем subprocess.run для команд
    if re.match(r'^\w+.*\$\(', stripped):
        # Это команда с подстановкой - пропускаем сложные случаи
        return f'    # TODO: Конвертировать команду: {stripped}'
    
    # Остальное - как комментарий с исходным кодом
    if stripped:
        return f'    # BASH: {stripped}'
    
    return None

# ============================================================================
# ОБЪЕДИНЕНИЕ ФАЙЛОВ
# ============================================================================

def extract_future_imports(python_code):
    """Извлекает __future__ импорты из Python кода"""
    future_imports = []
    other_lines = []
    
    for line in python_code.split('\n'):
        stripped = line.strip()
        if stripped.startswith('from __future__') or stripped.startswith('import __future__'):
            future_imports.append(line)
        else:
            other_lines.append(line)
    
    return future_imports, '\n'.join(other_lines)

def build_unified_file():
    """Создает объединенный файл"""
    
    print_step("Объединение файлов в единый Python скрипт...")
    
    # Создаем директорию build
    BUILD_DIR.mkdir(exist_ok=True)
    
    # Читаем исходные файлы
    print_step("Чтение исходных файлов...")
    astra_update_content = read_file_safe(ASTRA_UPDATE_SH)
    astra_install_content = read_file_safe(ASTRA_INSTALL_SH)
    astra_automation_content = read_file_safe(ASTRA_AUTOMATION_PY)
    
    # Извлекаем __future__ импорты из astra_automation.py
    future_imports, astra_automation_rest = extract_future_imports(astra_automation_content)
    
    # Конвертируем bash скрипты в Python (упрощенная версия)
    print_step("Конвертация bash скриптов в Python...")
    astra_update_python = convert_bash_to_python(astra_update_content, "astra_update")
    astra_install_python = convert_bash_to_python(astra_install_content, "astra_install")
    
    # Формируем объединенный файл
    print_step("Формирование объединенного файла...")
    
    unified_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FSA-AstraInstall - Единый исполняемый файл
Объединяет функциональность:
- astra_update.sh (обновление из сетевых источников)
- astra_install.sh (установка зависимостей)
- astra_automation.py (основное приложение)

Версия: V2.5.127 (2025.11.16)
Компания: ООО "НПА Вира-Реалтайм"
"""

# КРИТИЧНО: __future__ импорты должны быть в самом начале
{chr(10).join(future_imports) if future_imports else ''}

# ============================================================================
# БЛОК 1: КОД ИЗ astra_update.sh (конвертирован в Python)
# ============================================================================

def astra_update_main():
    """Функциональность из astra_update.sh"""
{chr(10).join("    " + line if line.strip() else line for line in astra_update_python.split(chr(10)))}

# ============================================================================
# БЛОК 2: КОД ИЗ astra_install.sh (конвертирован в Python)
# ============================================================================

def astra_install_main():
    """Функциональность из astra_install.sh"""
{chr(10).join("    " + line if line.strip() else line for line in astra_install_python.split(chr(10)))}

# ============================================================================
# БЛОК 3: КОД ИЗ astra_automation.py (оригинальный Python)
# ============================================================================

{astra_automation_rest}

# ============================================================================
# ГЛАВНАЯ ТОЧКА ВХОДА
# ============================================================================

if __name__ == '__main__':
    import sys
    
    # Определяем режим работы по аргументам
    if '--update-only' in sys.argv:
        astra_update_main()
    elif '--install-only' in sys.argv:
        astra_install_main()
    else:
        # Полный цикл: обновление -> установка -> запуск приложения
        astra_update_main()
        astra_install_main()
        main()  # Вызываем main() из astra_automation.py
'''
    
    # Записываем объединенный файл
    print_step(f"Запись объединенного файла: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(unified_content)
    
    print_success(f"Объединенный файл создан: {OUTPUT_FILE}")
    print_info(f"Размер файла: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")
    
    return OUTPUT_FILE

# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

if __name__ == '__main__':
    try:
        output_file = build_unified_file()
        print_success("Объединение завершено успешно!")
        sys.exit(0)
    except Exception as e:
        print_error(f"Ошибка объединения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

