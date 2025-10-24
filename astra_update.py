#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматического обновления FSA-AstraInstall для macOS
Использует AppleScript для обхода ограничений карантина
Версия: V2.3.73 (2025.10.24)
Компания: ООО "НПА Вира-Реалтайм"
"""

import os
import sys
import subprocess
import tkinter as tk
from datetime import datetime

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
            error_msg = f"Папка проекта не найдена: {source_path}"
            show_message("Ошибка", error_msg)
            return 1
        
        # Проверяем подключенный том
        if not os.path.exists(network_path):
            error_msg = f"Том Install не подключен: {network_path}"
            show_message("Ошибка", error_msg)
            return 1
        
        # Используем AppleScript для копирования файлов
        copied_files = []
        for file_name in files_to_copy:
            source_file = os.path.join(source_path, file_name)
            
            if not os.path.exists(source_file):
                error_msg = f"Файл не найден: {file_name}"
                show_message("Ошибка", error_msg)
                return 1
            
            # Создаем AppleScript для замены файла
            applescript = f'''
tell application "Finder"
    set sourceFile to POSIX file "{source_file}"
    set destFile to POSIX file "{network_path}/{file_name}"
    
    -- Удаляем старый файл если существует
    try
        delete destFile
    end try
    
    -- Копируем новый файл
    duplicate sourceFile to POSIX file "{network_path}/"
end tell
'''
            
            try:
                result = subprocess.run([
                    'osascript', '-e', applescript
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    copied_files.append(file_name)
                else:
                    error_msg = f"Ошибка копирования {file_name}: {result.stderr}"
                    show_message("Ошибка", error_msg)
                    return 1
                    
            except Exception as e:
                error_msg = f"Ошибка выполнения AppleScript для {file_name}: {e}"
                show_message("Ошибка", error_msg)
                return 1
        
        # Показываем окно успеха
        success_msg = f"Обновление завершено!\n\nОбновлено файлов: {len(copied_files)}\n{', '.join(copied_files)}"
        show_message("Обновление", success_msg)
        return 0
        
    except Exception as e:
        # Показываем окно с ошибкой
        error_msg = f"Общая ошибка: {str(e)}"
        show_message("Ошибка", error_msg)
        return 1

def show_message(title, message):
    """Показывает простое окно с сообщением"""
    try:
        root = tk.Tk()
        root.withdraw()  # Скрываем главное окно
        
        # Создаем диалог
        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        
        # Делаем окно поверх всех
        dialog.attributes('-topmost', True)
        dialog.lift()
        dialog.focus_force()
        
        # Центрируем окно
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")
        
        # Добавляем содержимое
        label = tk.Label(dialog, text=message, font=("Arial", 12), wraplength=350)
        label.pack(expand=True, padx=20, pady=20)
        
        # Добавляем кнопку OK
        button = tk.Button(dialog, text="OK", command=lambda: root.quit(), width=10)
        button.pack(pady=10)
        
        # Автозакрытие через 0,5 секунды
        dialog.after(500, lambda: root.quit())
        
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
        print(f"[MESSAGE] {title}: {message}")

if __name__ == "__main__":
    sys.exit(main())
