#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск GUI на macOS
Универсальный скрипт - работает из любого места
"""

import sys
import os
import importlib.util

def launch_gui():
    """Запуск GUI на macOS"""
    try:
        print("🚀 Запуск GUI на macOS...")
        
        # Получаем абсолютный путь к директории скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        astra_automation_path = os.path.join(script_dir, 'astra-automation.py')
        
        # Проверяем существование файла
        if not os.path.exists(astra_automation_path):
            print(f"❌ Файл не найден: {astra_automation_path}")
            print(f"   Убедитесь, что скрипт находится в папке с astra-automation.py")
            return False
        
        print(f"📁 Путь к модулю: {astra_automation_path}")
        
        # Импортируем модуль с дефисом
        spec = importlib.util.spec_from_file_location('astra_automation', astra_automation_path)
        astra_automation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(astra_automation)
        
        # Создаем экземпляр GUI напрямую, минуя main()
        gui = astra_automation.AutomationGUI(console_mode=False)
        
        print("✅ GUI создан успешно!")
        print("📱 Запускаем интерфейс...")
        
        # Запускаем GUI
        print("🔄 GUI запущен, ожидаем закрытия окна...")
        gui.run()
        print("✅ GUI закрыт")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка запуска GUI: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = launch_gui()
    if not success:
        sys.exit(1)
