#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск GUI на macOS
Универсальный скрипт - работает из любого места
Версия проекта: V2.3.74 (2025.10.16)
Компания: ООО "НПА Вира-Реалтайм"
"""

import sys
import os
import importlib.util

def launch_gui():
    """Запуск GUI на macOS"""
    try:
        print("Запуск GUI на macOS...")
        
        # Получаем абсолютный путь к директории скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        astra_automation_path = os.path.join(script_dir, 'astra_automation.py')
        
        # Проверяем существование файла
        if not os.path.exists(astra_automation_path):
            print(f"Файл не найден: {astra_automation_path}")
            print(f"   Убедитесь, что скрипт находится в папке с astra_automation.py")
            return False
        
        print(f"Путь к модулю: {astra_automation_path}")
        
        # Создаем папку Log если её нет
        log_dir = os.path.join(script_dir, 'Log')
        os.makedirs(log_dir, exist_ok=True)
        
        # Создаем лог файл с временной меткой
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"astra_automation_macos_{timestamp}.log")
        
        # Записываем процесс запуска в лог
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("FSA-AstraInstall Automation - ЗАПУСК ЧЕРЕЗ launch_gui_macos.py\n")
            f.write(f"Время запуска: {datetime.now()}\n")
            f.write(f"Рабочая директория: {script_dir}\n")
            f.write(f"Путь к модулю: {astra_automation_path}\n")
            f.write(f"Лог файл: {log_file}\n")
            f.write("=" * 80 + "\n")
            f.write("ПЕРЕДАЧА УПРАВЛЕНИЯ ОСНОВНОМУ ФАЙЛУ...\n")
            f.write("=" * 80 + "\n")
        
        print(f"Лог файл создан: {log_file}")
        
        # Устанавливаем аргументы командной строки ПЕРЕД импортом
        sys.argv = ['astra_automation.py', '--log-file', log_file]
        # Импортируем модуль с дефисом
        spec = importlib.util.spec_from_file_location('astra_automation', astra_automation_path)
        astra_automation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(astra_automation)
        
        # Записываем успешный импорт в лог
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Модуль astra_automation успешно импортирован\n")
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск main() с аргументами: {sys.argv}\n")
        
        # Запускаем через main() с передачей пути к логу
        astra_automation.main()
        
        # Записываем завершение в лог
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] main() завершен\n")
            f.write("=" * 80 + "\n")
            f.write("FSA-AstraInstall Automation - ЗАВЕРШЕНИЕ СЕССИИ\n")
            f.write("=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"Ошибка запуска GUI: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = launch_gui()
    if not success:
        sys.exit(1)
