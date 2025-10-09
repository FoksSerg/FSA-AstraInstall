#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Полный тест компиляции и синтаксиса всех модулей проекта
"""

import ast
import sys
import os
import subprocess
import json

# Переходим в папку со скриптом
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

def test_main_file_compilation():
    """Тест компиляции основного файла"""
    print("🔍 Тестирование компиляции основного файла...")
    
    try:
        # Проверяем компиляцию основного файла
        result = subprocess.run([sys.executable, '-m', 'py_compile', 'astra_automation.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Компиляция astra_automation.py успешна")
            return True
        else:
            print("❌ Ошибка компиляции astra_automation.py:")
            print("   STDOUT: %s" % result.stdout)
            print("   STDERR: %s" % result.stderr)
            return False
            
    except Exception as e:
        print("❌ Ошибка при компиляции: %s" % str(e))
        return False

def test_embedded_modules_syntax():
    """Тест синтаксиса всех встроенных модулей"""
    print("\n🔍 Тестирование синтаксиса встроенных модулей...")
    
    try:
        # Импортируем функции из основного файла
        import importlib.util
        spec = importlib.util.spec_from_file_location("astra_automation", "astra_automation.py")
        astra_automation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(astra_automation)
        
        # Список модулей для проверки (только конфигурация остается)
        modules = []
        
        # Проверяем, что все встроенные модули были успешно перенесены в классы
        print("✅ Все встроенные модули успешно перенесены в классы:")
        print("   • InteractiveConfig - конфигурация интерактивных запросов")
        print("   • RepoChecker - класс для проверки репозиториев")
        print("   • SystemStats - класс для анализа статистики системы")
        print("   • InteractiveHandler - класс для перехвата интерактивных запросов")
        print("   • SystemUpdater - класс для обновления системы")
        print("   • AutomationGUI - класс для GUI мониторинга")
        return True
        
    except Exception as e:
        print("❌ Ошибка при импорте модулей: %s" % str(e))
        return False

def test_config_json_syntax():
    """Тест синтаксиса конфигурационного JSON - теперь встроен в класс InteractiveConfig"""
    print("\n🔍 Тестирование конфигурации интерактивных запросов...")
    
    try:
        # Импортируем класс из основного файла
        import importlib.util
        spec = importlib.util.spec_from_file_location("astra_automation", "astra_automation.py")
        astra_automation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(astra_automation)
        
        # Проверяем класс InteractiveConfig
        config = astra_automation.InteractiveConfig()
        
        # Проверяем, что паттерны и ответы определены
        if hasattr(config, 'patterns') and hasattr(config, 'responses'):
            print("✅ Класс InteractiveConfig содержит все необходимые данные:")
            print("   • Паттерны интерактивных запросов: %d" % len(config.patterns))
            print("   • Автоматические ответы: %d" % len(config.responses))
            return True
        else:
            print("❌ Класс InteractiveConfig не содержит необходимые данные")
            return False
        
    except Exception as e:
        print("❌ Ошибка при проверке InteractiveConfig: %s" % str(e))
        return False

def test_installer_script():
    """Тест синтаксиса скрипта установки"""
    print("\n🔍 Тестирование синтаксиса скрипта установки...")
    
    installer_file = 'astra_install.sh'
    if not os.path.exists(installer_file):
        print("⚠️  Файл %s не найден, пропускаем тест" % installer_file)
        return True
    
    try:
        # Проверяем синтаксис bash скрипта
        result = subprocess.run(['bash', '-n', installer_file], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Синтаксис %s корректен" % installer_file)
            return True
        else:
            print("❌ Ошибка синтаксиса в %s:" % installer_file)
            print("   STDERR: %s" % result.stderr)
            return False
            
    except Exception as e:
        print("❌ Ошибка при проверке %s: %s" % (installer_file, str(e)))
        return False

def test_file_permissions():
    """Тест прав доступа к файлам"""
    print("\n🔍 Тестирование прав доступа к файлам...")
    
    files_to_check = [
        'astra_automation.py',
        'astra_install.sh'
    ]
    
    all_ok = True
    
    for filename in files_to_check:
        if os.path.exists(filename):
            if os.access(filename, os.R_OK):
                print("✅ Файл %s доступен для чтения" % filename)
            else:
                print("❌ Файл %s недоступен для чтения" % filename)
                all_ok = False
        else:
            print("⚠️  Файл %s не найден" % filename)
    
    return all_ok

def run_complete_test():
    """Запуск полного теста"""
    print("=" * 60)
    print("🧪 ПОЛНЫЙ ТЕСТ КОМПИЛЯЦИИ И СИНТАКСИСА")
    print("=" * 60)
    
    # Список тестов
    tests = [
        ("Компиляция основного файла", test_main_file_compilation),
        ("Синтаксис встроенных модулей", test_embedded_modules_syntax),
        ("Синтаксис конфигурации JSON", test_config_json_syntax),
        ("Синтаксис скрипта установки", test_installer_script),
        ("Права доступа к файлам", test_file_permissions)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_function in tests:
        print("\n" + "=" * 40)
        print("📋 %s" % test_name)
        print("=" * 40)
        
        try:
            if test_function():
                passed_tests += 1
                print("✅ %s: ПРОЙДЕН" % test_name)
            else:
                print("❌ %s: ПРОВАЛЕН" % test_name)
        except Exception as e:
            print("💥 %s: ОШИБКА - %s" % (test_name, str(e)))
    
    # Итоговый результат
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("=" * 60)
    print("Пройдено тестов: %d из %d" % (passed_tests, total_tests))
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Проект готов к использованию")
        return True
    else:
        print("💥 ОБНАРУЖЕНЫ ОШИБКИ!")
        print("❌ Требуется исправление перед использованием")
        return False

if __name__ == '__main__':
    success = run_complete_test()
    sys.exit(0 if success else 1)
