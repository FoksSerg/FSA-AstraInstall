#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Расширенный тест синтаксиса всех встроенных модулей
"""

import ast
import sys

def test_all_embedded_modules():
    """Тест синтаксиса всех встроенных модулей"""
    
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
            print("   Текст: %s" % e.text)
            all_passed = False
            
        except Exception as e:
            print("❌ Ошибка при проверке %s: %s" % (module_name, str(e)))
            all_passed = False
    
    # Проверяем конфигурационный файл JSON
    try:
        import json
        config_code = astra_automation.get_embedded_config()
        json.loads(config_code)
        print("✅ Синтаксис auto_responses.json корректен")
    except Exception as e:
        print("❌ Ошибка в auto_responses.json: %s" % str(e))
        all_passed = False
    
    return all_passed

if __name__ == '__main__':
    success = test_all_embedded_modules()
    
    if success:
        print("\n🎉 Все модули прошли проверку синтаксиса!")
    else:
        print("\n💥 Обнаружены ошибки синтаксиса!")
        sys.exit(1)
