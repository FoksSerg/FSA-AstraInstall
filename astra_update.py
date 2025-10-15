#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматического обновления FSA-AstraInstall для macOS
Копирует файлы в подключенный том
Версия: V2.2.58 (2025.10.15)
"""

import os
import sys
import shutil
import stat
import tkinter as tk

def main():
    """Основная функция для macOS"""
    
    # Пути для macOS
    source_path = "/Volumes/FSA-PRJ/Project/FSA-AstraInstall"
    network_path = "/Volumes/Install/ISO/Linux/Astra"
    
    # Файлы для копирования
    files_to_copy = [
        "astra_automation.py",
        "astra_install.sh", 
        "astra_update.sh"
    ]
    
    try:
        # Проверяем папку проекта
        if not os.path.exists(source_path):
            show_message("Ошибка", "Папка проекта не найдена")
            return 1
        
        # Проверяем подключенный том
        if not os.path.exists(network_path):
            show_message("Ошибка", "Том Install не подключен")
            return 1
        
        # Копируем файлы
        for file_name in files_to_copy:
            source_file = os.path.join(source_path, file_name)
            dest_file = os.path.join(network_path, file_name)
            
            if os.path.exists(source_file):
                shutil.copy2(source_file, dest_file)
            else:
                show_message("Ошибка", f"Файл не найден {file_name}")
                return 1
        
        # Устанавливаем права на выполнение
        for file_name in ["astra_install.sh", "astra_update.sh"]:
            file_path = os.path.join(network_path, file_name)
            if os.path.exists(file_path):
                os.chmod(file_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        
        # Показываем окно успеха
        show_message("Обновление", "Обновлено")
        return 0
        
    except Exception as e:
        # Показываем окно с ошибкой
        show_message("Ошибка", str(e))
        return 1

def show_message(title, message):
    """Показывает простое окно с сообщением"""
    try:
        root = tk.Tk()
        root.withdraw()  # Скрываем главное окно
        
        # Создаем диалог
        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        
        # Делаем окно поверх всех
        dialog.attributes('-topmost', True)
        dialog.lift()
        dialog.focus_force()
        
        # Центрируем окно
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (300 // 2)
        y = (dialog.winfo_screenheight() // 2) - (150 // 2)
        dialog.geometry(f"300x150+{x}+{y}")
        
        # Добавляем содержимое
        label = tk.Label(dialog, text=message, font=("Arial", 12), wraplength=250)
        label.pack(expand=True, padx=20, pady=20)
        
        # Добавляем кнопку OK
        button = tk.Button(dialog, text="OK", command=lambda: root.quit(), width=10)
        button.pack(pady=10)
        
        # Автозакрытие через 2 секунды
        dialog.after(2000, lambda: root.quit())
        
        # Показываем окно
        root.mainloop()
        
        # Принудительно закрываем все tkinter процессы
        try:
            root.destroy()
            dialog.destroy()
        except:
            pass
        
        # Завершаем процесс
        os._exit(0)
        
    except:
        # Fallback - просто выводим в консоль
        print(message)

if __name__ == "__main__":
    sys.exit(main())