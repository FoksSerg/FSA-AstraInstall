#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест синтаксиса встроенного кода gui_monitor.py
"""

import ast
import sys

def test_gui_monitor_syntax():
    """Тест синтаксиса встроенного кода gui_monitor.py"""
    
    # Импортируем функцию из основного файла
    import importlib.util
    spec = importlib.util.spec_from_file_location("astra_automation", "astra-automation.py")
    astra_automation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(astra_automation)
    
    # Получаем встроенный код
    code = astra_automation.get_embedded_gui_monitor()
    
    try:
        # Парсим код для проверки синтаксиса
        ast.parse(code)
        print("✅ Синтаксис встроенного кода gui_monitor.py корректен")
        return True
    except SyntaxError as e:
        print("❌ Ошибка синтаксиса в строке %d: %s" % (e.lineno, e.msg))
        print("   Текст: %s" % e.text)
        return False
    except Exception as e:
        print("❌ Ошибка при проверке синтаксиса: %s" % str(e))
        return False

if __name__ == '__main__':
    test_gui_monitor_syntax()
