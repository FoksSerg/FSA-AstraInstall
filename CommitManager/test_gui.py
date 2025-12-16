#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки GUI CommitManager
"""

import sys
import os

# Добавляем путь к корню проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_imports():
    """Тест импортов"""
    print("=== Тест импортов ===")
    try:
        from CommitManager import ConfigManager, ProjectConfig, CommitExecutor, CommitAnalyzer, CommitManagerGUI
        print("✓ Все модули импортированы успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_manager():
    """Тест ConfigManager"""
    print("\n=== Тест ConfigManager ===")
    try:
        from CommitManager import ConfigManager
        cm = ConfigManager()
        print(f"✓ ConfigManager создан")
        print(f"  Путь к конфигу: {cm.config_file_path}")
        
        # Создаем конфигурацию по умолчанию
        default_config = cm.create_default_fsa_config()
        print(f"✓ Конфигурация по умолчанию создана: {default_config.name}")
        print(f"  Путь проекта: {default_config.path}")
        print(f"  Ключевых файлов: {len(default_config.key_files)}")
        print(f"  Бинарных файлов: {len(default_config.binary_files)}")
        
        # Валидация
        is_valid, error = default_config.validate()
        if is_valid:
            print(f"✓ Конфигурация валидна")
        else:
            print(f"⚠ Конфигурация не валидна: {error}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_creation():
    """Тест создания GUI (без запуска mainloop)"""
    print("\n=== Тест создания GUI ===")
    try:
        import tkinter as tk
        from CommitManager import CommitManagerGUI
        
        # Создаем корневое окно и сразу скрываем
        root = tk.Tk()
        root.withdraw()
        
        # Пробуем создать GUI
        gui = CommitManagerGUI()
        print("✓ GUI создан успешно")
        print(f"  Размер окна: {gui.root.winfo_width()}x{gui.root.winfo_height()}")
        print(f"  Количество вкладок: {len(gui.notebook.tabs())}")
        
        # Закрываем окно
        root.destroy()
        gui.root.destroy()
        print("✓ GUI закрыт")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Запуск тестов CommitManager GUI\n")
    
    results = []
    results.append(("Импорты", test_imports()))
    results.append(("ConfigManager", test_config_manager()))
    results.append(("GUI создание", test_gui_creation()))
    
    print("\n" + "="*50)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print("="*50)
    
    for name, result in results:
        status = "✓ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("="*50)
    if all_passed:
        print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        sys.exit(0)
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        sys.exit(1)
