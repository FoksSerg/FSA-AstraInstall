#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск GUI на macOS
Простой запуск основного скрипта FSA-AstraInstall.py с параметрами
Версия проекта: V3.1.159 (2025.12.06)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import sys
import os
import subprocess
import platform
from datetime import datetime

def main():
    """Простой запуск основного скрипта FSA-AstraInstall.py на macOS"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # FSA-AstraInstall.py находится в родительской директории (корень проекта)
    project_root = os.path.dirname(script_dir)
    main_script_path = os.path.join(project_root, 'FSA-AstraInstall.py')
    
    # Проверяем существование файла
    if not os.path.exists(main_script_path):
        print(f"Файл не найден: {main_script_path}")
        print(f"Убедитесь, что файл FSA-AstraInstall.py находится в директории: {project_root}")
        return False
    
    # Проверяем, что мы на macOS
    if platform.system() != "Darwin":
        print(f"[WARNING] Этот скрипт предназначен для macOS, обнаружена система: {platform.system()}")
        print("[WARNING] На Linux используйте прямой запуск FSA-AstraInstall.py")
    
    # Создаем папку Log если её нет (для логов с префиксом macos_)
    # Папка Log находится в корне проекта, а не в RunScript
    log_dir = os.path.join(project_root, 'Log')
    os.makedirs(log_dir, exist_ok=True)
    
    # Создаем лог файл с временной меткой и префиксом macos_
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"analysis_macos_{timestamp}.log")
    
    print(f"Запуск FSA-AstraInstall.py на macOS...")
    print(f"Лог файл: {log_file}")
    
    # ПРОСТО ЗАПУСКАЕМ СКРИПТ С ПАРАМЕТРАМИ (без sudo)
    # На macOS проверка root пропускается автоматически по платформе
    try:
        result = subprocess.run([
            sys.executable, 
            main_script_path, 
            '--log-file', 
            log_file
        ], check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)