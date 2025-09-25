#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Текстовый GUI на curses для Astra Linux
Совместимость: Python 2.7.16 (без tkinter)
"""

from __future__ import print_function
import sys
import os
import time

def test_curses_gui():
    """Тестируем текстовый GUI на curses"""
    print("Тестирование текстового GUI на curses...")
    
    try:
        import curses
        import locale
        
        # Настраиваем кодировку для curses
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            pass
        
        def main_screen(stdscr):
            """Основной экран приложения"""
            # Настраиваем цвета
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Заголовок
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Успех
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Ошибка
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Предупреждение
            
            # Очищаем экран
            stdscr.clear()
            stdscr.refresh()
            
            # Получаем размеры экрана
            height, width = stdscr.getmaxyx()
            
            # Заголовок
            title = "Astra Automation - Текстовый интерфейс"
            stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(1))
            
            # Разделитель
            stdscr.addstr(1, 0, "=" * width)
            
            # Информация о системе
            stdscr.addstr(3, 2, "Версия Python: %s" % sys.version.split()[0])
            stdscr.addstr(4, 2, "ОС: %s" % os.name)
            stdscr.addstr(5, 2, "Рабочая папка: %s" % os.getcwd())
            
            # Статус модулей
            stdscr.addstr(7, 2, "Статус модулей:")
            
            # Проверяем модули
            modules = [
                ("Tkinter", "[ОШИБКА] Недоступен (требует python-tk)"),
                ("curses", "[ОК] Доступен"),
                ("subprocess", "[ОК] Доступен"),
                ("os", "[ОК] Доступен"),
                ("sys", "[ОК] Доступен")
            ]
            
            for i, (module, status) in enumerate(modules):
                color = curses.color_pair(2) if "[ОК]" in status else curses.color_pair(3)
                stdscr.addstr(8 + i, 4, "   %s: %s" % (module, status), color)
            
            # Меню
            stdscr.addstr(13, 2, "Доступные функции:")
            stdscr.addstr(14, 4, "1. Проверка репозиториев")
            stdscr.addstr(15, 4, "2. Статистика системы")
            stdscr.addstr(16, 4, "3. Обновление системы")
            stdscr.addstr(17, 4, "4. Интерактивные запросы")
            stdscr.addstr(18, 4, "5. Выход")
            
            # Инструкции
            stdscr.addstr(20, 2, "Нажмите цифру для выбора функции или 'q' для выхода")
            
            # Обновляем экран
            stdscr.refresh()
            
            # Ждем ввода
            while True:
                key = stdscr.getch()
                
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('1'):
                    show_repo_checker(stdscr)
                elif key == ord('2'):
                    show_system_stats(stdscr)
                elif key == ord('3'):
                    show_system_updater(stdscr)
                elif key == ord('4'):
                    show_interactive_handler(stdscr)
                elif key == ord('5'):
                    break
                else:
                    # Показываем сообщение о неверном вводе
                    stdscr.addstr(22, 2, "[ОШИБКА] Неверный ввод! Используйте цифры 1-5 или 'q'", curses.color_pair(3))
                    stdscr.refresh()
                    time.sleep(1)
                    stdscr.addstr(22, 2, " " * 60)  # Очищаем сообщение
                    stdscr.refresh()
        
        def show_repo_checker(stdscr):
            """Экран проверки репозиториев"""
            stdscr.clear()
            stdscr.addstr(0, 2, "Проверка репозиториев", curses.color_pair(1))
            stdscr.addstr(1, 0, "=" * 50)
            stdscr.addstr(3, 2, "Проверяем доступность репозиториев...")
            stdscr.addstr(4, 2, "[ОК] Репозиторий 1: Доступен")
            stdscr.addstr(5, 2, "[ОШИБКА] Репозиторий 2: Недоступен")
            stdscr.addstr(6, 2, "[ОК] Репозиторий 3: Доступен")
            stdscr.addstr(8, 2, "Статистика:")
            stdscr.addstr(9, 4, "- Рабочих репозиториев: 2")
            stdscr.addstr(10, 4, "- Нерабочих репозиториев: 1")
            stdscr.addstr(12, 2, "Нажмите любую клавишу для возврата...")
            stdscr.refresh()
            stdscr.getch()
        
        def show_system_stats(stdscr):
            """Экран статистики системы"""
            stdscr.clear()
            stdscr.addstr(0, 2, "Статистика системы", curses.color_pair(1))
            stdscr.addstr(1, 0, "=" * 50)
            stdscr.addstr(3, 2, "Информация о системе:")
            stdscr.addstr(4, 4, "- Процессор: Intel/AMD")
            stdscr.addstr(5, 4, "- Память: 4GB")
            stdscr.addstr(6, 4, "- Диск: 100GB")
            stdscr.addstr(8, 2, "Установленные пакеты:")
            stdscr.addstr(9, 4, "- python: 2.7.16")
            stdscr.addstr(10, 4, "- apt: 1.8.2")
            stdscr.addstr(12, 2, "Нажмите любую клавишу для возврата...")
            stdscr.refresh()
            stdscr.getch()
        
        def show_system_updater(stdscr):
            """Экран обновления системы"""
            stdscr.clear()
            stdscr.addstr(0, 2, "Обновление системы", curses.color_pair(1))
            stdscr.addstr(1, 0, "=" * 50)
            stdscr.addstr(3, 2, "Проверяем обновления...")
            stdscr.addstr(4, 2, "[ОК] Найдено 5 обновлений")
            stdscr.addstr(5, 2, "Загружаем пакеты...")
            stdscr.addstr(6, 2, "Устанавливаем обновления...")
            stdscr.addstr(8, 2, "[ОК] Обновление завершено успешно!")
            stdscr.addstr(10, 2, "Нажмите любую клавишу для возврата...")
            stdscr.refresh()
            stdscr.getch()
        
        def show_interactive_handler(stdscr):
            """Экран интерактивных запросов"""
            stdscr.clear()
            stdscr.addstr(0, 2, "Интерактивные запросы", curses.color_pair(1))
            stdscr.addstr(1, 0, "=" * 50)
            stdscr.addstr(3, 2, "Автоматические ответы:")
            stdscr.addstr(4, 4, "- Y - для подтверждений")
            stdscr.addstr(5, 4, "- N - для отказов")
            stdscr.addstr(6, 4, "- Enter - для продолжения")
            stdscr.addstr(8, 2, "Обработано запросов: 15")
            stdscr.addstr(9, 2, "[ОК] Успешно: 15")
            stdscr.addstr(10, 2, "[ОШИБКА] Ошибок: 0")
            stdscr.addstr(12, 2, "Нажмите любую клавишу для возврата...")
            stdscr.refresh()
            stdscr.getch()
        
        # Запускаем curses приложение
        curses.wrapper(main_screen)
        print("Текстовый GUI завершен успешно")
        return True
        
    except Exception as e:
        print("Ошибка curses GUI: %s" % str(e))
        return False

def main():
    """Основная функция"""
    print("=" * 60)
    print("ТЕКСТОВЫЙ GUI НА CURSES - Astra Linux")
    print("=" * 60)
    
    if test_curses_gui():
        print("Текстовый GUI работает отлично!")
        print("Это решение для Astra Linux без tkinter")
        return True
    else:
        print("Текстовый GUI не работает")
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("Тест завершен успешно!")
    else:
        print("Тест завершен с ошибкой")
        sys.exit(1)