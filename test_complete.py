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
        result = subprocess.run([sys.executable, '-m', 'py_compile', 'astra-automation.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Компиляция astra-automation.py успешна")
            return True
        else:
            print("❌ Ошибка компиляции astra-automation.py:")
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
        spec = importlib.util.spec_from_file_location("astra_automation", "astra-automation.py")
        astra_automation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(astra_automation)
        
        # Список модулей для проверки
        modules = [
            ('repo_checker.py', astra_automation.get_embedded_repo_checker),
            ('system_stats.py', astra_automation.get_embedded_system_stats),
            ('interactive_handler.py', astra_automation.get_embedded_interactive_handler),
            ('system_updater.py', astra_automation.get_embedded_system_updater),
            ('gui_monitor.py', astra_automation.get_embedded_gui_monitor)
        ]
        
        all_passed = True
        
        for module_name, get_function in modules:
            try:
                # Получаем встроенный код
                code = get_function()
                
                # Парсим код для проверки синтаксиса
                ast.parse(code)
                print("✅ Синтаксис %s корректен" % module_name)
                
            except SyntaxError as e:
                print("❌ Ошибка синтаксиса в %s, строка %d: %s" % (module_name, e.lineno, e.msg))
                if e.text:
                    print("   Текст: %s" % e.text.strip())
                all_passed = False
                
            except Exception as e:
                print("❌ Ошибка при проверке %s: %s" % (module_name, str(e)))
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print("❌ Ошибка при импорте модулей: %s" % str(e))
        return False

def test_config_json_syntax():
    """Тест синтаксиса конфигурационного JSON"""
    print("\n🔍 Тестирование синтаксиса конфигурационного файла...")
    
    try:
        # Импортируем функцию из основного файла
        import importlib.util
        spec = importlib.util.spec_from_file_location("astra_automation", "astra-automation.py")
        astra_automation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(astra_automation)
        
        # Проверяем JSON конфигурацию
        config_code = astra_automation.get_embedded_config()
        json.loads(config_code)
        print("✅ Синтаксис auto_responses.json корректен")
        return True
        
    except json.JSONDecodeError as e:
        print("❌ Ошибка JSON в auto_responses.json, строка %d: %s" % (e.lineno, e.msg))
        return False
    except Exception as e:
        print("❌ Ошибка при проверке auto_responses.json: %s" % str(e))
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
        'astra-automation.py',
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
