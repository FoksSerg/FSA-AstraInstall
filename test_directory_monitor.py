#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки DirectoryMonitor
"""

import os
import tempfile
import shutil
import time
import sys

# Импортируем классы из astra-automation.py
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('astra_automation', 'astra-automation.py')
    astra_automation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(astra_automation)
    
    print("✅ Модуль загружен")
    # Проверяем наличие классов
    if hasattr(astra_automation, 'DirectoryMonitor'):
        print("✅ Класс DirectoryMonitor найден")
        DirectoryMonitor = astra_automation.DirectoryMonitor
    else:
        raise AttributeError("module 'astra_automation' has no attribute 'DirectoryMonitor'")
    
    if hasattr(astra_automation, 'DirectorySnapshot'):
        print("✅ Класс DirectorySnapshot найден")
        DirectorySnapshot = astra_automation.DirectorySnapshot
    else:
        raise AttributeError("module 'astra_automation' has no attribute 'DirectorySnapshot'")

except ImportError as e:
    print(f"❌ Ошибка: {e}")
    sys.exit(1)
except AttributeError as e:
    print(f"❌ Ошибка: {e}")
    sys.exit(1)

def test_directory_monitor():
    """Тестирование функциональности DirectoryMonitor"""
    print("🧪 Тестирование DirectoryMonitor...")
    
    # Создаем временную директорию для тестирования
    test_dir = tempfile.mkdtemp(prefix="test_monitor_")
    print(f"📁 Тестовая директория: {test_dir}")
    
    try:
        # Создаем монитор
        monitor = DirectoryMonitor()
        
        # Создаем начальные файлы
        test_file1 = os.path.join(test_dir, "file1.txt")
        test_file2 = os.path.join(test_dir, "file2.txt")
        test_subdir = os.path.join(test_dir, "subdir")
        
        with open(test_file1, 'w') as f:
            f.write("Содержимое файла 1")
        
        with open(test_file2, 'w') as f:
            f.write("Содержимое файла 2")
        
        os.makedirs(test_subdir)
        
        # Начинаем мониторинг
        print("\n🔍 Начинаем мониторинг...")
        monitor.start_monitoring(test_dir)
        
        # Делаем изменения
        print("\n📝 Вносим изменения...")
        
        # Изменяем файл
        with open(test_file1, 'w') as f:
            f.write("Измененное содержимое файла 1")
        
        # Создаем новый файл
        test_file3 = os.path.join(test_dir, "file3.txt")
        with open(test_file3, 'w') as f:
            f.write("Новый файл")
        
        # Создаем новую поддиректорию
        test_subdir2 = os.path.join(test_dir, "subdir2")
        os.makedirs(test_subdir2)
        
        # Создаем файл в новой поддиректории
        test_file4 = os.path.join(test_subdir2, "file4.txt")
        with open(test_file4, 'w') as f:
            f.write("Файл в поддиректории")
        
        # Удаляем файл
        os.remove(test_file2)
        
        # Проверяем изменения
        print("\n🔍 Проверяем изменения...")
        changes = monitor.check_changes(test_dir)
        
        if changes:
            print("📊 Обнаружены изменения:")
            formatted = monitor.format_changes(changes)
            print(formatted)
        else:
            print("❌ Изменения не обнаружены")
        
        # Проверяем полные изменения
        print("\n📊 Полные изменения с начала мониторинга:")
        total_changes = monitor.get_total_changes(test_dir)
        if total_changes:
            formatted_total = monitor.format_changes(total_changes)
            print(formatted_total)
        
        print("\n✅ Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Очищаем тестовую директорию
        shutil.rmtree(test_dir)
        print(f"🧹 Тестовая директория удалена: {test_dir}")

if __name__ == "__main__":
    test_directory_monitor()
