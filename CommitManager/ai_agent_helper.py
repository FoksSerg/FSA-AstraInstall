#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вспомогательный модуль для интеграции AI-агента в процесс создания коммита
Версия: V3.4.185 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import subprocess
import platform
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Попытка импортировать pyperclip для работы с буфером обмена
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def get_cursor_agent_hotkey() -> Optional[str]:
    """
    Читает настройки Cursor и возвращает горячую клавишу для режима Agent
    
    Returns:
        Строка с горячей клавишей (например, "cmd+1") или None если не найдена
    """
    try:
        keybindings_path = os.path.expanduser("~/Library/Application Support/Cursor/User/keybindings.json")
        if not os.path.exists(keybindings_path):
            return None
        
        with open(keybindings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Удаляем комментарии из JSON
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('//'):
                    cleaned_lines.append(line)
            cleaned_content = '\n'.join(cleaned_lines)
            
            keybindings = json.loads(cleaned_content)
            
            # Ищем горячую клавишу для composerMode.agent
            for binding in keybindings:
                if binding.get('command') == 'composerMode.agent':
                    return binding.get('key')
        
        return None
    except Exception:
        return None


def create_ai_analysis_request(project_dir: str, analysis_data: str, config_name: str) -> str:
    """
    Создает файл-запрос для AI-агента на анализ изменений
    
    Args:
        project_dir: Директория проекта
        analysis_data: Данные анализа из .commit_analysis_data.txt
        config_name: Имя проекта из конфигурации
        
    Returns:
        Путь к созданному файлу-запросу
    """
    request_file = os.path.join(project_dir, '.ai_commit_request.txt')
    
    prompt = f"""Проанализируй изменения в файлах проекта и создай краткое описание коммита на русском языке.

Формат описания:
[Заголовок коммита - опишите кратко основные изменения]

Кратко, что изменили (списком):

Имя_файла1:
- Краткое описание изменения 1
- Краткое описание изменения 2

Имя_файла2:
- Краткое описание изменения 1

Описание удаленных классов/модулей:
- Нет удаленных компонентов (или описание если есть)

Проект: {config_name}
Дата: {datetime.now().strftime('%Y.%m.%d')}

ВАЖНО: НЕ комментировать изменения дат и версий в файлах проекта - эти изменения делаются автоматически.
В описании указывать ТОЛЬКО реальные изменения кода, логики, правил, структуры и т.д.

Данные изменений:
{analysis_data}
"""
    
    with open(request_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    return request_file


def create_ai_agent_trigger(project_dir: str, request_file: str) -> str:
    """
    Создает специальный файл-триггер для принудительного запуска AI-агента
    Этот файл будет автоматически обработан AI-агентом как новый запрос в новом чате
    
    Args:
        project_dir: Директория проекта
        request_file: Путь к файлу .ai_commit_request.txt
        
    Returns:
        Путь к созданному файлу-триггеру
    """
    trigger_file = os.path.join(project_dir, '.ai_agent_trigger.txt')
    commit_message_file = os.path.join(project_dir, 'commit_message.txt')
    
    # Читаем содержимое файла-запроса, чтобы включить его в триггер
    request_content = ""
    try:
        if os.path.exists(request_file):
            with open(request_file, 'r', encoding='utf-8') as f:
                request_content = f.read()
    except Exception:
        request_content = f"Файл запроса: {request_file}"
    
    # Извлекаем только данные изменений из запроса
    analysis_data = ""
    if 'Данные изменений:' in request_content:
        analysis_data = request_content.split('Данные изменений:', 1)[1].strip()
    else:
        analysis_data = request_content
    
    # Определяем относительный путь к commit_message.txt от корня проекта
    # Если project_dir содержит CommitTest, то путь будет CommitTest/commit_message.txt
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # От CommitManager до корня
    if project_dir.startswith(project_root):
        rel_path = os.path.relpath(commit_message_file, project_root)
    else:
        # Если project_dir вне корня, используем только имя файла
        rel_path = 'commit_message.txt'
    
    # Создаем триггер в формате прямого запроса ко мне
    # Агент должен использовать встроенный механизм Cursor для анализа git changes
    trigger_content = f"""{rel_path} Проанализируй изменения в файлах проекта используя встроенный механизм Cursor (Changes / Source Control / git diff) и создай краткое описание коммита на русском языке.

ВАЖНО: Используй встроенный механизм Cursor для анализа изменений (Changes panel, git diff since last commit), а НЕ полагайся только на этот текст.

Формат описания:
[Заголовок коммита - опишите кратко основные изменения]

Кратко, что изменили (списком):

Имя_файла1:
- Краткое описание изменения 1
- Краткое описание изменения 2

Имя_файла2:
- Краткое описание изменения 1

Описание удаленных классов/модулей:
- Нет удаленных компонентов (или описание если есть)

Проект: FSA-AstraInstall
Дата: {datetime.now().strftime('%Y.%m.%d')}

ВАЖНО: 
- НЕ комментировать изменения дат и версий в файлах проекта - эти изменения делаются автоматически.
- В описании указывать ТОЛЬКО реальные изменения кода, логики, правил, структуры и т.д.
- Создай файл {rel_path} в корне проекта с описанием коммита.
"""
    
    with open(trigger_file, 'w', encoding='utf-8') as f:
        f.write(trigger_content)
    
    return trigger_file


def check_ai_analysis_complete(project_dir: str, start_time: float) -> bool:
    """
    Проверяет, завершен ли анализ AI-агентом
    
    Args:
        project_dir: Директория проекта
        start_time: Время начала ожидания (timestamp)
        
    Returns:
        True если commit_message.txt создан AI-агентом ПОСЛЕ начала ожидания
    """
    commit_message_file = os.path.join(project_dir, 'commit_message.txt')
    
    if not os.path.exists(commit_message_file) or os.path.getsize(commit_message_file) == 0:
        return False
    
    # Проверяем время модификации файла
    # Если файл был создан/изменен ПОСЛЕ start_time, значит это AI-агент его создал
    try:
        file_mtime = os.path.getmtime(commit_message_file)
        # Добавляем небольшую задержку (1 сек) для учета погрешности
        return file_mtime >= (start_time - 1.0)
    except Exception:
        # Если не удалось получить время, считаем что файл не создан AI-агентом
        return False


def close_files_in_cursor(file_paths: List[str]) -> bool:
    """
    Закрывает файлы в Cursor после обработки
    
    Args:
        file_paths: Список путей к файлам для закрытия
        
    Returns:
        True если файлы успешно закрыты, False если не удалось
    """
    if not file_paths:
        return True
    
    try:
        if platform.system() == 'Darwin':  # macOS
            # Пытаемся закрыть вкладки через AppleScript
            # ВАЖНО: AppleScript может закрыть только активную вкладку через Cmd+W
            # Нельзя закрыть конкретный файл по имени, только если он активен
            
            # Пытаемся активировать Cursor и закрыть активную вкладку несколько раз
            # (в надежде что нужные файлы будут закрыты)
            script = '''
            tell application "Cursor"
                activate
            end tell
            
            tell application "System Events"
                tell process "Cursor"
                    -- Пытаемся закрыть активную вкладку
                    -- Это закроет только активную вкладку, не конкретный файл
                    keystroke "w" using {command down}
                end tell
            end tell
            '''
            
            # Пытаемся закрыть несколько раз (на случай если файлы открыты последовательно)
            closed_count = 0
            for _ in range(min(len(file_paths), 3)):  # Максимум 3 попытки
                try:
                    result = subprocess.run(['osascript', '-e', script], 
                                          capture_output=True, 
                                          timeout=2,
                                          check=False)
                    if result.returncode == 0:
                        closed_count += 1
                    time.sleep(0.3)  # Небольшая задержка между попытками
                except Exception:
                    pass
            
            # Возвращаем True только если хотя бы одна попытка была успешной
            # Но это не гарантирует закрытие конкретных файлов
            return closed_count > 0
            
        elif platform.system() == 'Windows':
            # На Windows можно использовать команды Cursor
            # Но пока просто возвращаем False (не реализовано)
            return False
        else:  # Linux
            return False
            
    except Exception:
        # В случае ошибки возвращаем False
        return False


def open_file_in_cursor(file_path: str) -> bool:
    """
    Автоматически открывает файл в Cursor через CLI
    
    Args:
        file_path: Путь к файлу для открытия
        
    Returns:
        True если файл успешно открыт
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            return False
        
        # Абсолютный путь
        abs_path = os.path.abspath(file_path)
        
        # Пытаемся открыть через Cursor CLI
        # Cursor обычно устанавливает команду 'cursor' в PATH
        try:
            # macOS/Linux: cursor <file> --wait (открывает и ждет)
            # Windows: cursor <file>
            if platform.system() == 'Windows':
                # Windows: используем shell=True
                subprocess.Popen(['cursor', abs_path], 
                               shell=True,
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            else:
                # macOS/Linux: пробуем открыть файл в существующем окне Cursor
                # Используем --goto для перехода к файлу в открытом окне
                try:
                    subprocess.Popen(['cursor', '--goto', abs_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    # Даем время на открытие
                    import time
                    time.sleep(0.5)
                    return True
                except FileNotFoundError:
                    # Если --goto не работает, пробуем обычное открытие
                    subprocess.Popen(['cursor', abs_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    import time
                    time.sleep(0.5)
                    return True
            return True
        except FileNotFoundError:
            # Команда 'cursor' не найдена, пробуем альтернативные способы
            # macOS: open -a Cursor
            if platform.system() == 'Darwin':
                try:
                    subprocess.Popen(['open', '-a', 'Cursor', abs_path],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    import time
                    time.sleep(0.5)
                    return True
                except Exception:
                    pass
            
            # Linux: xdg-open или прямой вызов
            if platform.system() == 'Linux':
                try:
                    subprocess.Popen(['xdg-open', abs_path],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    import time
                    time.sleep(0.5)
                    return True
                except Exception:
                    pass
            
            return False
            
    except Exception:
        return False


def create_new_chat_in_cursor(message: str) -> bool:
    """
    Создает новый диалог в Cursor и отправляет запрос агенту
    
    Args:
        message: Текст запроса для отправки агенту
        
    Returns:
        True если диалог успешно создан и запрос отправлен
    """
    if platform.system() != 'Darwin':  # Только для macOS
        return False
    
    try:
        # Копируем сообщение в буфер обмена
        if HAS_PYPERCLIP:
            try:
                pyperclip.copy(message)
            except Exception:
                # Fallback на pbcopy
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=message)
                process.wait()
        else:
            # Используем pbcopy напрямую
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=message)
            process.wait()
        
        # Получаем горячую клавишу для режима Agent из настроек Cursor
        agent_hotkey = get_cursor_agent_hotkey()
        # По умолчанию используем cmd+1 (найдено в настройках пользователя)
        if not agent_hotkey:
            agent_hotkey = "cmd+1"
        
        # Парсим горячую клавишу для использования в AppleScript
        # Формат: "cmd+1" -> keystroke "1" using {command down}
        hotkey_parts = agent_hotkey.lower().split('+')
        key_char = hotkey_parts[-1]  # Последняя часть - это клавиша
        modifiers = []
        if 'cmd' in hotkey_parts or 'command' in hotkey_parts:
            modifiers.append('command down')
        if 'ctrl' in hotkey_parts or 'control' in hotkey_parts:
            modifiers.append('control down')
        if 'shift' in hotkey_parts:
            modifiers.append('shift down')
        if 'alt' in hotkey_parts or 'option' in hotkey_parts:
            modifiers.append('option down')
        
        # Формируем строку модификаторов для AppleScript
        if modifiers:
            modifiers_str = '{' + ', '.join(modifiers) + '}'
        else:
            modifiers_str = ''
        
        # Для цифр используем key code, для букв - keystroke
        # key code 18 = цифра 1
        if key_char == '1':
            if modifiers_str:
                hotkey_line = f'key code 18 using {modifiers_str}'
            else:
                hotkey_line = 'key code 18'
        else:
            if modifiers_str:
                hotkey_line = f'keystroke "{key_char}" using {modifiers_str}'
            else:
                hotkey_line = f'keystroke "{key_char}"'
        
        # AppleScript для создания нового чата в Cursor
        # Используем правильную комбинацию: Shift + Command + L для создания нового агента/чата
        # Затем переключаем режим на "Agent" используя горячую клавишу из настроек
        
        script = f'''
        tell application "Cursor"
            activate
        end tell
        
        tell application "System Events"
            tell process "Cursor"
                set frontmost to true
                delay 1.0
                -- Создаем новый агент/чат напрямую (Shift + Cmd + L)
                keystroke "l" using {{command down, shift down}}
                delay 2.5
                
                -- Переключаем режим на "Agent" используя горячую клавишу из настроек ({agent_hotkey})
                {hotkey_line}
                delay 1.5
                
                -- Убеждаемся, что фокус на поле ввода (Tab для перехода к полю ввода)
                key code 48
                delay 0.3
                
                -- Вставляем текст из буфера обмена (Cmd+V)
                keystroke "v" using {{command down}}
                delay 0.8
                
                -- Отправляем запрос (Enter)
                key code 36
            end tell
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, 
                              timeout=10,
                              check=False)
        
        return result.returncode == 0
        
    except Exception as e:
        # В случае ошибки возвращаем False
        return False


def send_to_ai_agent_automatically(request_file: str, project_dir: str) -> bool:
    """
    Автоматически отправляет запрос AI-агенту через создание нового диалога в Cursor
    Только текстовое сообщение, без открытия файлов
    
    Args:
        request_file: Путь к файлу .ai_commit_request.txt (не используется, оставлен для совместимости)
        project_dir: Директория проекта
        
    Returns:
        True если запрос успешно отправлен
    """
    try:
        # Читаем содержимое файла-триггера
        trigger_file = os.path.join(project_dir, '.ai_agent_trigger.txt')
        
        if os.path.exists(trigger_file):
            with open(trigger_file, 'r', encoding='utf-8') as f:
                trigger_content = f.read()
            
            # Создаем новый диалог и отправляем запрос (только текст, без открытия файлов)
            return create_new_chat_in_cursor(trigger_content)
        
        return False
        
    except Exception:
        return False
