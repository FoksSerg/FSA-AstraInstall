#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запускающий скрипт для GUI PackageManager
Версия: V3.4.176 (2025.12.08)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import sys
import os
from pathlib import Path

# Получаем директорию скрипта (RunScript/)
SCRIPT_DIR = Path(__file__).parent.absolute()
# Получаем корень проекта (родительская директория RunScript/)
PROJECT_DIR = SCRIPT_DIR.parent

# Проверяем, что PackageManager существует
package_manager_path = PROJECT_DIR / "PackageManager"
if not package_manager_path.exists():
    print(f"❌ ОШИБКА: Модуль PackageManager не найден в {package_manager_path}")
    print(f"Убедитесь, что скрипт запускается из правильной директории проекта")
    sys.exit(1)

# Добавляем путь к проекту в sys.path (если его там еще нет)
project_path_str = str(PROJECT_DIR)
if project_path_str not in sys.path:
    sys.path.insert(0, project_path_str)

# Переходим в директорию проекта
os.chdir(PROJECT_DIR)

# Запускаем GUI
if __name__ == "__main__":
    try:
        from PackageManager.gui import main
        
        sys.exit(main() or 0)
    except ImportError as e:
        print(f"❌ ОШИБКА: Не удалось импортировать PackageManager.gui: {e}")
        print(f"Проверьте, что модуль PackageManager находится в {PROJECT_DIR}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ОШИБКА при запуске GUI: {e}")
        sys.exit(1)

