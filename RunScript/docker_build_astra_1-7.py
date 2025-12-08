#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматической сборки FSA-AstraInstall на удаленном Docker для платформы astra-1.7
Версия: V3.3.170 (2025.12.07)
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

# Проверяем, что DockerManager существует
docker_manager_path = PROJECT_DIR / "DockerManager"
if not docker_manager_path.exists():
    print(f"❌ ОШИБКА: Модуль DockerManager не найден в {docker_manager_path}")
    print(f"Убедитесь, что скрипт запускается из правильной директории проекта")
    sys.exit(1)

# Добавляем путь к проекту в sys.path (если его там еще нет)
project_path_str = str(PROJECT_DIR)
if project_path_str not in sys.path:
    sys.path.insert(0, project_path_str)

# Переходим в директорию проекта
os.chdir(PROJECT_DIR)

# Запускаем сборку
if __name__ == "__main__":
    try:
        from DockerManager.cli import main
        
        # Устанавливаем параметры для сборки на удаленном Docker для astra-1.7
        sys.argv = [
            sys.argv[0],
            "--project", "FSA-AstraInstall",
            "--platform", "astra-1.7",
            "--remote",
            # "--rebuild"  # Пересобрать образ с wmctrl
        ]
        
        print("=" * 60)
        print("=== Автоматическая сборка FSA-AstraInstall ===")
        print("=== Платформа: astra-1.7 (Debian Buster) ===")
        print("=== Режим: удаленная сборка на Docker ===")
        print("=" * 60)
        print()
        
        exit_code = main()
        sys.exit(exit_code)
        
    except ImportError as e:
        print(f"❌ ОШИБКА: Не удалось импортировать DockerManager.cli: {e}")
        print(f"Проверьте, что модуль DockerManager находится в {PROJECT_DIR}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ОШИБКА при запуске сборки: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

