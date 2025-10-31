#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск GUI на macOS
Простой запуск основного скрипта с параметрами
Версия проекта: V2.4.91 (2025.10.30)
Компания: ООО "НПА Вира-Реалтайм"
"""

import sys
import os
import subprocess
from datetime import datetime

def main():
    """Простой запуск основного скрипта"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    astra_automation_path = os.path.join(script_dir, 'astra_automation.py')
    
    # Проверяем существование файла
    if not os.path.exists(astra_automation_path):
        print(f"Файл не найден: {astra_automation_path}")
        return False
    
    # Создаем папку Log если её нет
    log_dir = os.path.join(script_dir, 'Log')
    os.makedirs(log_dir, exist_ok=True)
    
    # Создаем лог файл с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"astra_automation_macos_{timestamp}.log")
    
    print(f"Запуск основного скрипта...")
    print(f"Лог файл: {log_file}")
    
    # ПРОСТО ЗАПУСКАЕМ СКРИПТ С ПАРАМЕТРАМИ
    try:
        result = subprocess.run([
            sys.executable, 
            astra_automation_path, 
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