#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для демонстрации вкладки Wine & Astra.IDE
Запускается БЕЗ прав root для тестирования интерфейса
"""

import os
import sys

# Импортируем класс проверки
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_wine_tab():
    """Тестирование вкладки Wine"""
    try:
        import tkinter as tk
        from tkinter import ttk
        print("[OK] Tkinter доступен")
    except ImportError:
        print("[ERR] Tkinter не установлен. Установите: sudo apt-get install python3-tk")
        return False
    
    # Создаем окно
    root = tk.Tk()
    root.title("Wine & Astra.IDE - Тестовый интерфейс")
    root.geometry("900x500")
    
    # Создаем вкладку (упрощенная версия)
    wine_frame = tk.Frame(root)
    wine_frame.pack(fill=tk.BOTH, expand=True)
    
    # Заголовок
    title_frame = tk.LabelFrame(wine_frame, text="Статус установки Wine и Astra.IDE")
    title_frame.pack(fill=tk.X, padx=10, pady=5)
    
    info_label = tk.Label(title_frame, 
                          text="Проверка наличия и статуса установленных Wine компонентов и Astra.IDE",
                          font=('Arial', 10))
    info_label.pack(padx=10, pady=5)
    
    # Кнопка проверки
    button_frame = tk.Frame(wine_frame)
    button_frame.pack(fill=tk.X, padx=10, pady=5)
    
    def simulate_check():
        status_label.config(text="Проверка завершена (тестовый режим)")
        # Заполняем тестовыми данными
        tree.delete(*tree.get_children())
        
        test_data = [
            ('Wine Astraregul', '[ERR]', '/opt/wine-astraregul/bin/wine'),
            ('Wine 9.0', '[ERR]', '/opt/wine-9.0/bin/wine'),
            ('ptrace_scope', '[OK]', '/proc/sys/kernel/yama/ptrace_scope'),
            ('WINEPREFIX', '[ERR]', '~/.wine-astraregul'),
            ('Astra.IDE', '[ERR]', 'WINEPREFIX/drive_c/Program Files/AstraRegul'),
            ('Скрипт запуска', '[ERR]', '~/start-astraide.sh'),
            ('Ярлык рабочего стола', '[ERR]', '~/Desktop/AstraRegul.desktop')
        ]
        
        for component, status, path in test_data:
            item = tree.insert('', tk.END, values=(component, status, path))
            if status == '[OK]':
                tree.item(item, tags=('ok',))
            else:
                tree.item(item, tags=('error',))
        
        tree.tag_configure('ok', foreground='green')
        tree.tag_configure('error', foreground='red')
        
        # Обновляем сводку
        summary_text.config(state=tk.NORMAL)
        summary_text.delete('1.0', tk.END)
        summary_text.insert(tk.END, "[ERR] Wine не установлен или настроен неправильно\n", 'error_tag')
        summary_text.insert(tk.END, "      Требуется установка Wine пакетов\n")
        summary_text.tag_configure('error_tag', foreground='red', font=('Courier', 9, 'bold'))
        summary_text.config(state=tk.DISABLED)
    
    check_button = tk.Button(button_frame, 
                            text="Проверить компоненты", 
                            command=simulate_check,
                            font=('Arial', 10, 'bold'))
    check_button.pack(side=tk.LEFT, padx=5)
    
    status_label = tk.Label(button_frame, 
                           text="Нажмите кнопку для проверки (тестовый режим без root)",
                           font=('Arial', 9))
    status_label.pack(side=tk.LEFT, padx=10)
    
    # Область статуса компонентов
    status_frame = tk.LabelFrame(wine_frame, text="Статус компонентов")
    status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Создаем таблицу статусов
    columns = ('component', 'status', 'path')
    tree = ttk.Treeview(status_frame, columns=columns, show='headings', height=8)
    
    # Настраиваем колонки
    tree.heading('component', text='Компонент')
    tree.heading('status', text='Статус')
    tree.heading('path', text='Путь/Детали')
    
    tree.column('component', width=200)
    tree.column('status', width=100)
    tree.column('path', width=500)
    
    # Добавляем скроллбар
    scrollbar = tk.Scrollbar(status_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
    
    # Начальные данные
    initial_components = [
        ('Wine Astraregul', 'Не проверено', '/opt/wine-astraregul/bin/wine'),
        ('Wine 9.0', 'Не проверено', '/opt/wine-9.0/bin/wine'),
        ('ptrace_scope', 'Не проверено', '/proc/sys/kernel/yama/ptrace_scope'),
        ('WINEPREFIX', 'Не проверено', '~/.wine-astraregul'),
        ('Astra.IDE', 'Не проверено', 'WINEPREFIX/drive_c/Program Files/AstraRegul'),
        ('Скрипт запуска', 'Не проверено', '~/start-astraide.sh'),
        ('Ярлык рабочего стола', 'Не проверено', '~/Desktop/AstraRegul.desktop')
    ]
    
    for component, status, path in initial_components:
        tree.insert('', tk.END, values=(component, status, path))
    
    # Итоговая сводка
    summary_frame = tk.LabelFrame(wine_frame, text="Итоговая сводка")
    summary_frame.pack(fill=tk.X, padx=10, pady=5)
    
    summary_text = tk.Text(summary_frame, height=4, wrap=tk.WORD, font=('Courier', 9))
    summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    summary_text.insert(tk.END, "Нажмите кнопку 'Проверить компоненты' для запуска проверки\n")
    summary_text.insert(tk.END, "Проверка покажет какие компоненты установлены и готовы к работе")
    summary_text.config(state=tk.DISABLED)
    
    print("\n[INFO] Тестовое окно запущено")
    print("[INFO] Нажмите кнопку 'Проверить компоненты' для симуляции проверки")
    print("[INFO] Закройте окно когда закончите\n")
    
    root.mainloop()
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ВКЛАДКИ Wine & Astra.IDE")
    print("=" * 60)
    print("\nЭто тестовый интерфейс, работает БЕЗ прав root")
    print("Показывает как будет выглядеть новая вкладка в GUI\n")
    
    test_wine_tab()
