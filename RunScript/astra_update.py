#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматического обновления FSA-AstraInstall для macOS
Использует AppleScript для обхода ограничений карантина
Версия: V3.3.168 (2025.12.08)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
import subprocess
import time

# ============================================================================
# ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ К СЕРВЕРУ (настройка)
# ============================================================================
SMB_SERVER = "10.10.55.77"          # IP адрес или имя SMB сервера
SMB_SHARE = "Install"                # Имя SMB шары
SMB_PATH = "ISO/Linux/Astra"         # Путь к папке с файлами на сервере
SMB_MOUNT_POINT = "/Volumes/Install"  # Точка монтирования SMB тома (macOS)
SOURCE_PATH = "/Volumes/FSA-PRJ/Project/FSA-AstraInstall"  # Путь к исходной папке проекта
# ============================================================================

def get_volume():
    """
    Получает текущую громкость системы (0-100)
    Возвращает None в случае ошибки
    """
    try:
        applescript = 'output volume of (get volume settings)'
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None

def set_volume(level):
    """
    Устанавливает громкость системы (0-100)
    """
    try:
        # Ограничиваем уровень от 0 до 100
        level = max(0, min(100, int(level)))
        applescript = f'set volume output volume {level}'
        subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            timeout=5
        )
        return True
    except Exception:
        return False

def play_sound(sound_type):
    """
    Воспроизводит системный звук macOS
    Временно включает громкость если она отключена/минимальная
    sound_type: 'success' - трель успеха, 'error' - печальный звук ошибки
    """
    try:
        if sound_type == 'success':
            # Трель успеха - Glass.aiff (приятный стеклянный звук)
            sound_file = "/System/Library/Sounds/Glass.aiff"
        elif sound_type == 'error':
            # Печальный звук ошибки - Blow.aiff (более продолжительный звук)
            sound_file = "/System/Library/Sounds/Blow.aiff"
        else:
            return
        
        # Проверяем существование файла
        if not os.path.exists(sound_file):
            # Fallback на другие звуки
            if sound_type == 'success':
                sound_file = "/System/Library/Sounds/Ping.aiff"
            else:
                # Fallback для ошибки - Hero.aiff (продолжительный звук)
                sound_file = "/System/Library/Sounds/Hero.aiff"
            
            if not os.path.exists(sound_file):
                return
        
        # Получаем текущую громкость
        original_volume = get_volume()
        volume_was_changed = False
        
        # Если громкость слишком низкая (< 10%), временно включаем
        if original_volume is not None and original_volume < 10:
            # Устанавливаем комфортную громкость (30%)
            if set_volume(30):
                volume_was_changed = True
        
        # Воспроизводим звук синхронно (ждем завершения)
        try:
            subprocess.run(
                ['afplay', sound_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
        except subprocess.TimeoutExpired:
            pass
        
        # Возвращаем исходную громкость если меняли
        if volume_was_changed and original_volume is not None:
            # Небольшая задержка чтобы звук точно закончился
            time.sleep(0.1)
            set_volume(original_volume)
            
    except Exception:
        # Игнорируем ошибки воспроизведения звука
        pass

def connect_smb_volume():
    """Подключает SMB том на macOS"""
    
    # Метод 1: Через AppleScript (Finder)
    try:
        applescript = f'''
        tell application "Finder"
            try
                mount volume "smb://{SMB_SERVER}/{SMB_SHARE}"
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
            'mount_smbfs', f'//{SMB_SERVER}/{SMB_SHARE}', SMB_MOUNT_POINT
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
            'open', f'smb://{SMB_SERVER}/{SMB_SHARE}'
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
    source_path = SOURCE_PATH
    network_path = f"{SMB_MOUNT_POINT}/{SMB_PATH}"
    
    # Файлы для копирования
    files_to_copy = [
        "FSA-AstraInstall-1-7",
        "FSA-AstraInstall-1-8",
    ]
    
    try:
        # Проверяем папку проекта
        if not os.path.exists(source_path):
            error_msg = f"Папка проекта не найдена: {source_path}"
            print(f"Ошибка: {error_msg}")
            play_sound('error')
            return 1
        
        # Проверяем подключенный том и подключаем если нужно
        if not os.path.exists(network_path):
            print(f"Том {SMB_SHARE} не подключен, пытаемся подключить...")
            if connect_smb_volume():
                print("SMB том подключен успешно")
                # Ждем немного чтобы том успел смонтироваться
                time.sleep(2)
                
                # Проверяем еще раз
                if not os.path.exists(network_path):
                    error_msg = f"Не удалось подключить том {SMB_SHARE}: {network_path}"
                    print(f"Ошибка: {error_msg}")
                    play_sound('error')
                    return 1
            else:
                error_msg = f"Не удалось подключить SMB том smb://{SMB_SERVER}/{SMB_SHARE}"
                print(f"Ошибка: {error_msg}")
                play_sound('error')
                return 1
        
        # Используем AppleScript для копирования файлов
        copied_files = []
        for file_name in files_to_copy:
            source_file = os.path.join(source_path, file_name)
            
            if not os.path.exists(source_file):
                error_msg = f"Файл не найден: {file_name}"
                print(f"Ошибка: {error_msg}")
                play_sound('error')
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
                    print(f"Файл {file_name} успешно скопирован")
                else:
                    error_msg = f"Ошибка копирования {file_name}: {result.stderr}"
                    print(f"Ошибка: {error_msg}")
                    play_sound('error')
                    return 1
                    
            except Exception as e:
                error_msg = f"Ошибка выполнения AppleScript для {file_name}: {e}"
                print(f"Ошибка: {error_msg}")
                play_sound('error')
                return 1
        
        # Успешное завершение
        success_msg = f"Обновление завершено! Обновлено файлов: {len(copied_files)}\n{', '.join(copied_files)}\nSMB том подключен автоматически"
        print(success_msg)
        play_sound('success')
        return 0
        
    except Exception as e:
        # Общая ошибка
        error_msg = f"Общая ошибка: {str(e)}"
        print(f"Ошибка: {error_msg}")
        play_sound('error')
        return 1

if __name__ == "__main__":
    sys.exit(main())
