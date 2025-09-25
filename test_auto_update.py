#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест автоматического обновления Python с tkinter
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import sys
import os
import subprocess

def check_tkinter():
    """Проверяем доступность tkinter"""
    try:
        import Tkinter as tk
        print("✅ tkinter доступен")
        return True
    except ImportError:
        print("❌ tkinter недоступен")
        return False

def update_python_with_tkinter():
    """Обновляем Python с поддержкой tkinter"""
    print("🔄 Обновляем Python с поддержкой tkinter...")
    
    try:
        # Сначала исправляем систему
        print("   Исправляем поврежденную систему...")
        result = subprocess.call(['apt', '--fix-broken', 'install', '-y'], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result == 0:
            print("✅ Система исправлена")
        else:
            print("⚠️ Не удалось исправить систему, продолжаем...")
        
        # Обновляем только Python и tkinter (без обновления всех репозиториев)
        print("   Обновляем только Python и tkinter...")
        packages = [
            'python',
            'python-tk'
        ]
        
        for package in packages:
            print("   Устанавливаем: %s" % package)
            try:
                process = subprocess.Popen(['apt-get', 'install', '-y', package], 
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    print("✅ %s установлен" % package)
                else:
                    print("⚠️ Не удалось установить %s" % package)
                    if stderr:
                        print("   Ошибка: %s" % stderr.strip())
            except Exception as e:
                print("❌ Ошибка установки %s: %s" % (package, str(e)))
        
        # Проверяем что tkinter теперь работает
        if check_tkinter():
            print("✅ tkinter теперь работает!")
            return True
        else:
            print("❌ tkinter все еще не работает после обновления")
            return False
        
    except Exception as e:
        print("❌ Ошибка обновления: %s" % str(e))
        return False

def restart_program():
    """Перезапускаем программу"""
    print("🔄 Перезапускаем программу с обновленным Python...")
    
    try:
        # Перезапускаем текущую программу
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print("❌ Ошибка перезапуска: %s" % str(e))
        return False

def run_gui_mode():
    """Запускаем графический режим"""
    print("🖥️ Запуск графического режима...")
    
    try:
        import Tkinter as tk
        import tkMessageBox as messagebox
        
        # Создаем главное окно
        root = tk.Tk()
        root.title("Astra Automation - GUI Mode")
        root.geometry("500x300")
        
        # Создаем основной фрейм
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_label = tk.Label(main_frame, text="Astra Automation", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Информация
        info_label = tk.Label(main_frame, text="Графический интерфейс работает!")
        info_label.pack(pady=(0, 20))
        
        # Кнопка тестирования
        test_button = tk.Button(main_frame, text="Тест функций", 
                               command=lambda: messagebox.showinfo("Тест", "GUI работает!"))
        test_button.pack(pady=(0, 10))
        
        # Кнопка выхода
        exit_button = tk.Button(main_frame, text="Выход", command=root.quit)
        exit_button.pack()
        
        print("✅ GUI запущен успешно")
        root.mainloop()
        return True
        
    except Exception as e:
        print("❌ Ошибка GUI: %s" % str(e))
        return False

def run_console_mode():
    """Запускаем консольный режим"""
    print("💻 Запуск консольного режима...")
    
    print("=" * 50)
    print("ASTRA AUTOMATION - CONSOLE MODE")
    print("=" * 50)
    print("Python версия: %s" % sys.version)
    print("ОС: %s" % os.name)
    print("Рабочая папка: %s" % os.getcwd())
    print()
    print("Доступные функции:")
    print("1. Проверка репозиториев")
    print("2. Статистика системы")
    print("3. Обновление системы")
    print("4. Интерактивные запросы")
    print()
    print("✅ Консольный режим работает")
    return True

def main():
    """Основная функция с автоматическим обновлением"""
    print("=" * 60)
    print("ASTRA AUTOMATION - AUTO UPDATE PYTHON")
    print("=" * 60)
    
    # Проверяем права root
    if os.geteuid() != 0:
        print("❌ Требуются права root для обновления пакетов")
        print("Запустите: sudo python test_auto_update.py")
        return False
    
    # Проверяем tkinter
    if check_tkinter():
        print("🎉 tkinter доступен! Запускаем GUI...")
        return run_gui_mode()
    else:
        print("⚠️ tkinter недоступен, пробуем обновить...")
        
        # Обновляем Python
        if update_python_with_tkinter():
            print("🔄 Перезапускаем программу...")
            restart_program()
        else:
            print("❌ Не удалось обновить Python, запускаем консольный режим")
            return run_console_mode()
    
    return True

if __name__ == '__main__':
    success = main()
    if success:
        print("✅ Программа завершена успешно")
    else:
        print("❌ Программа завершена с ошибкой")
        sys.exit(1)
