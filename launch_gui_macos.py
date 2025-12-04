#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск GUI на macOS
Простой запуск основного скрипта FSA-AstraInstall.py с параметрами
Версия проекта: V3.1.156 (2025.12.05)
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
    main_script_path = os.path.join(script_dir, 'FSA-AstraInstall.py')
    
    # Проверяем существование файла
    if not os.path.exists(main_script_path):
        print(f"Файл не найден: {main_script_path}")
        print(f"Убедитесь, что файл FSA-AstraInstall.py находится в директории: {script_dir}")
        return False
    
    # Проверяем, что мы на macOS
    if platform.system() != "Darwin":
        print(f"[WARNING] Этот скрипт предназначен для macOS, обнаружена система: {platform.system()}")
        print("[WARNING] На Linux используйте прямой запуск FSA-AstraInstall.py")
    
    # Создаем папку Log если её нет
    log_dir = os.path.join(script_dir, 'Log')
    os.makedirs(log_dir, exist_ok=True)
    
    # Создаем лог файл с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"FSA-AstraInstall_macos_{timestamp}.log")
    
    print(f"Запуск FSA-AstraInstall.py на macOS...")
    print(f"Лог файл: {log_file}")
    
    # На macOS не нужны права root, передаём переменную окружения для отключения проверки
    env = os.environ.copy()
    env['FSA_SKIP_ROOT_CHECK'] = '1'  # Флаг для отключения проверки root на macOS
    
    # ПРОСТО ЗАПУСКАЕМ СКРИПТ С ПАРАМЕТРАМИ (без sudo)
    try:
        result = subprocess.run([
            sys.executable, 
            main_script_path, 
            '--log-file', 
            log_file
        ], env=env, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)