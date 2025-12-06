#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI интерфейс для DockerManager
Версия: V3.1.160 (2025.12.06)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import sys
import argparse
from .build_runner import build
from .config import PROJECTS, BUILD_PLATFORMS

def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description="DockerManager - Управление Docker сборками"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Запустить GUI приложение"
    )
    
    parser.add_argument(
        "--project",
        choices=list(PROJECTS.keys()),
        default="FSA-AstraInstall",
        help="Проект для сборки"
    )
    
    parser.add_argument(
        "--platform",
        choices=list(BUILD_PLATFORMS.keys()),
        help="Платформа для сборки"
    )
    
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Запустить сборку на удаленном сервере"
    )
    
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Принудительно пересобрать Docker образ (удалить старый и создать новый)"
    )
    
    args = parser.parse_args()
    
    # Если запрошен GUI - запускаем его
    if args.gui:
        from .build_manager_gui import BuildManagerGUI
        app = BuildManagerGUI()
        app.run()
        return 0
    
    # Иначе CLI режим
    if not args.platform:
        parser.error("--platform обязателен для CLI режима (или используйте --gui)")
    
    # Запускаем сборку
    success = build(args.project, args.platform, remote=args.remote, rebuild=args.rebuild)
    
    if success:
        print("\n" + "=" * 60)
        print("=== Сборка завершена успешно ===")
        print("=" * 60)
        
        # ВРЕМЕННО: Автоматическое обновление на SMB сервере после удалённой сборки
        if args.remote and args.project == "FSA-AstraInstall":
            print("\n[INFO] Запуск автоматического обновления на SMB сервере...")
            try:
                import subprocess
                import os
                from pathlib import Path
                
                # Получаем путь к скрипту обновления
                project_dir = Path(__file__).parent.parent
                update_script = project_dir / "RunScript" / "astra_update.py"
                
                if update_script.exists():
                    print(f"[INFO] Запуск скрипта: {update_script}")
                    result = subprocess.run(
                        [sys.executable, str(update_script)],
                        capture_output=False,
                        timeout=120
                    )
                    if result.returncode == 0:
                        print("[OK] Обновление на SMB сервере завершено успешно")
                    else:
                        print(f"[WARNING] Скрипт обновления завершился с кодом: {result.returncode}")
                else:
                    print(f"[WARNING] Скрипт обновления не найден: {update_script}")
            except Exception as e:
                print(f"[WARNING] Ошибка при запуске скрипта обновления: {e}")
        
        return 0
    else:
        print("\n" + "=" * 60)
        print("=== Сборка завершена с ошибками ===")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())

