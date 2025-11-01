#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматического обновления FSA-AstraInstall для macOS
Использует AppleScript для обхода ограничений карантина
Версия: V2.4.95 (2025.10.30)
Компания: ООО "НПА Вира-Реалтайм"
"""

import os
import sys
import subprocess
import tkinter as tk
from datetime import datetime

def connect_smb_volume():
    """Подключает SMB том на macOS"""
    
    # Метод 1: Через AppleScript (Finder)
    try:
        applescript = '''
        tell application "Finder"
            try
                mount volume "smb://10.10.55.77/Install"
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        '''
        
        result = subprocess.run([
            'osascript', '-e', applescript
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and "success" in result.stdout:
            print("SMB том подключен через Finder")
            return True
        else:
            print(f"Finder не смог подключить SMB: {result.stderr}")
            
    except Exception as e:
        print(f"Ошибка AppleScript: {e}")
    
    # Метод 2: Через командную строку (mount_smbfs)
    try:
        print("Пробуем подключить через mount_smbfs...")
        result = subprocess.run([
            'mount_smbfs', '//10.10.55.77/Install', '/Volumes/Install'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("SMB том подключен через mount_smbfs")
            return True
        else:
            print(f"mount_smbfs не смог подключить: {result.stderr}")
            
    except Exception as e:
        print(f"Ошибка mount_smbfs: {e}")
    
    # Метод 3: Через open команду
    try:
        print("Пробуем подключить через open...")
        result = subprocess.run([
            'open', 'smb://10.10.55.77/Install'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("SMB том подключен через open")
            return True
        else:
            print(f"open не смог подключить: {result.stderr}")
            
    except Exception as e:
        print(f"Ошибка open: {e}")
    
    print("Все методы подключения SMB не сработали")
    return False

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
        
        # Проверяем подключенный том и подключаем если нужно
        if not os.path.exists(network_path):
            print("Том Install не подключен, пытаемся подключить...")
            if connect_smb_volume():
                print("SMB том подключен успешно")
                # Ждем немного чтобы том успел смонтироваться
                import time
                time.sleep(2)
                
                # Проверяем еще раз
                if not os.path.exists(network_path):
                    error_msg = f"Не удалось подключить том Install: {network_path}"
                    show_message("Ошибка", error_msg)
                    return 1
            else:
                error_msg = f"Не удалось подключить SMB том smb://10.10.55.77/Install"
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
        success_msg = f"Обновление завершено!\n\nОбновлено файлов: {len(copied_files)}\n{', '.join(copied_files)}\n\nSMB том подключен автоматически"
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
