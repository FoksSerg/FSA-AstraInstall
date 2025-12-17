#!/usr/bin/env python3
"""
Тестовый скрипт для проверки автоматического создания чата в Cursor
и переключения в режим Agent с вставкой тестового сообщения
"""

import sys
import os
import subprocess
import platform
import json

# Добавляем путь к модулю CommitManager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def get_cursor_agent_hotkey() -> str:
    """Получает горячую клавишу для режима Agent из настроек Cursor"""
    try:
        keybindings_path = os.path.expanduser("~/Library/Application Support/Cursor/User/keybindings.json")
        if not os.path.exists(keybindings_path):
            return "cmd+1"  # Значение по умолчанию
        
        with open(keybindings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Удаляем комментарии (строки, начинающиеся с //)
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('//'):
                    cleaned_lines.append(line)
            cleaned_content = '\n'.join(cleaned_lines)
            
            keybindings = json.loads(cleaned_content)
            for binding in keybindings:
                if binding.get('command') == 'composerMode.agent':
                    return binding.get('key', 'cmd+1')
        
        return "cmd+1"  # Значение по умолчанию
    except Exception as e:
        print(f"⚠️  Не удалось прочитать настройки Cursor: {e}")
        return "cmd+1"  # Значение по умолчанию


def test_create_agent_chat(message: str) -> bool:
    """
    Создает новый чат в Cursor, переключает в режим Agent и вставляет сообщение
    
    Args:
        message: Сообщение для вставки и отправки
        
    Returns:
        True если операция успешна
    """
    if platform.system() != 'Darwin':  # Только для macOS
        print("❌ Этот скрипт работает только на macOS")
        return False
    
    try:
        print("📋 Копирую сообщение в буфер обмена...")
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
        print("✓ Сообщение скопировано в буфер обмена")
        
        # Получаем горячую клавишу для режима Agent
        agent_hotkey = get_cursor_agent_hotkey()
        print(f"⌨️  Найдена горячая клавиша для Agent: {agent_hotkey}")
        
        # Парсим горячую клавишу для использования в AppleScript
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
        
        print(f"   Детали горячей клавиши:")
        print(f"   - Клавиша: '{key_char}'")
        print(f"   - Модификаторы: {modifiers}")
        
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
            print(f"   - Используется key code 18 (цифра 1)")
        else:
            if modifiers_str:
                hotkey_line = f'keystroke "{key_char}" using {modifiers_str}'
            else:
                hotkey_line = f'keystroke "{key_char}"'
            print(f"   - Используется keystroke '{key_char}'")
        
        print("🚀 Активирую Cursor...")
        # AppleScript для создания нового чата в Cursor и переключения в режим Agent
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
                
                -- Вставляем текст из буфера обмена (Cmd+V)
                keystroke "v" using {{command down}}
                delay 0.8
                
                -- Отправляем запрос (Enter)
                key code 36
            end tell
        end tell
        '''
        
        print("⏳ Выполняю AppleScript...")
        print("   - Активация Cursor (1.0 сек)")
        print("   - Создание нового чата Shift+Cmd+L (2.5 сек)")
        print(f"   - Переключение в режим Agent ({agent_hotkey}) (1.5 сек)")
        print("   - Вставка сообщения Cmd+V (0.8 сек)")
        print("   - Отправка запроса Enter")
        print()
        print("⚠️  После выполнения проверьте в Cursor:")
        print("   1. Открылся ли новый чат")
        print("   2. Находится ли чат в режиме Agent (не Ask)")
        print("   3. Вставлено ли сообщение и отправлен ли запрос")
        
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, 
                              timeout=10,
                              check=False)
        
        if result.returncode == 0:
            print()
            print("✓ Скрипт выполнен успешно!")
            if result.stdout:
                output = result.stdout.decode('utf-8', errors='ignore').strip()
                if output:
                    print(f"   Вывод: {output}")
            return True
        else:
            print()
            print(f"❌ Ошибка выполнения AppleScript (код: {result.returncode})")
            if result.stderr:
                error = result.stderr.decode('utf-8', errors='ignore').strip()
                if error:
                    print(f"   Ошибка: {error}")
            if result.stdout:
                output = result.stdout.decode('utf-8', errors='ignore').strip()
                if output:
                    print(f"   Вывод: {output}")
            return False
        
    except subprocess.TimeoutExpired:
        print("❌ Таймаут выполнения AppleScript")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция"""
    print("=" * 60)
    print("Тест создания нового чата, переключения в режим Agent")
    print("и отправки сообщения")
    print("=" * 60)
    print()
    
    # Тестовое сообщение
    test_message = """@commit_message.txt Проанализируй изменения в файлах проекта и создай краткое описание коммита на русском языке.

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
Дата: 2025.12.17

ВАЖНО: НЕ комментировать изменения дат и версий в файлах проекта - эти изменения делаются автоматически.
В описании указывать ТОЛЬКО реальные изменения кода, логики, правил, структуры и т.д.

Это тестовое сообщение для проверки автоматического создания чата."""
    
    print(f"📝 Тестовое сообщение ({len(test_message)} символов):")
    print("-" * 60)
    print(test_message[:200] + "..." if len(test_message) > 200 else test_message)
    print("-" * 60)
    print()
    
    # Проверяем, есть ли аргумент --auto для автоматического запуска
    auto_mode = '--auto' in sys.argv
    
    print("⚠️  Внимание: Убедитесь, что Cursor открыт и готов к работе!")
    if not auto_mode:
        print("   Нажмите Enter для продолжения или Ctrl+C для отмены...")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            print("\n❌ Отменено")
            return
    else:
        print("   Автоматический режим: запуск через 2 секунды...")
        import time
        time.sleep(2)
    
    print()
    success = test_create_agent_chat(test_message)
    
    print()
    print("=" * 60)
    if success:
        print("✓ Тест завершен успешно!")
        print("   Проверьте в Cursor:")
        print("   - Открылся ли новый чат")
        print("   - Находится ли чат в режиме Agent (не Ask)")
        print("   - Вставлено ли сообщение и отправлен ли запрос")
    else:
        print("❌ Тест завершен с ошибками")
        print("   Проверьте логи выше для диагностики проблемы.")
    print("=" * 60)


if __name__ == '__main__':
    main()
