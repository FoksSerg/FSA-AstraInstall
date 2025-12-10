#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматической сборки FSA-AstraInstall на удаленном Docker для всех платформ astra
Версия: V3.4.174 (2025.12.08)
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
        
        # Платформы для сборки
        platforms = [
            ("astra-1.7", "Debian Buster"),
            ("astra-1.8", "Debian Bookworm")
        ]
        
        print("=" * 60)
        print("=== Автоматическая сборка FSA-AstraInstall ===")
        print("=== Режим: удаленная сборка на Docker ===")
        print(f"=== Платформ для сборки: {len(platforms)} ===")
        print("=" * 60)
        print()
        
        exit_codes = []
        
        for platform_id, platform_desc in platforms:
            print()
            print("=" * 60)
            print(f"=== Сборка для платформы: {platform_id} ({platform_desc}) ===")
            print("=" * 60)
            print()
            
            # Устанавливаем параметры для сборки на удаленном Docker
            sys.argv = [
                sys.argv[0],
                "--project", "FSA-AstraInstall",
                "--platform", platform_id,
                "--remote",
                # "--rebuild"  # Пересобрать образ с wmctrl
            ]
            
            exit_code = main()
            exit_codes.append((platform_id, exit_code))
            
            if exit_code != 0:
                print()
                print(f"⚠️  ВНИМАНИЕ: Сборка для {platform_id} завершилась с кодом {exit_code}")
            else:
                print()
                print(f"✓ Сборка для {platform_id} завершена успешно")
        
        # Итоговая информация
        print()
        print("=" * 60)
        print("=== ИТОГИ СБОРКИ ===")
        print("=" * 60)
        
        all_success = True
        for platform_id, exit_code in exit_codes:
            status = "✓ УСПЕШНО" if exit_code == 0 else "✗ ОШИБКА"
            print(f"  {platform_id}: {status} (код: {exit_code})")
            if exit_code != 0:
                all_success = False
        
        print("=" * 60)
        
        # Возвращаем код ошибки, если хотя бы одна сборка не удалась
        if all_success:
            print("✓ Все сборки завершены успешно!")
            sys.exit(0)
        else:
            print("✗ Некоторые сборки завершились с ошибками")
            sys.exit(1)
        
    except ImportError as e:
        print(f"❌ ОШИБКА: Не удалось импортировать DockerManager.cli: {e}")
        print(f"Проверьте, что модуль DockerManager находится в {PROJECT_DIR}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ОШИБКА при запуске сборки: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

