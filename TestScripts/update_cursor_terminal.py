#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления настроек терминала Cursor
"""
import os
import json

# Путь к настройкам Cursor
settings_path = os.path.expanduser("~/Library/Application Support/Cursor/User/settings.json")

print(f"Читаю настройки из: {settings_path}")

# Читаем текущие настройки
if os.path.exists(settings_path):
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    print("✓ Текущие настройки загружены")
else:
    settings = {}
    print("⚠ Файл настроек не найден, создаю новый")

# Добавляем настройки терминала для использования bash
settings["terminal.integrated.defaultProfile.osx"] = "bash"
settings["terminal.integrated.profiles.osx"] = {
    "bash": {
        "path": "/bin/bash",
        "args": ["--noprofile", "--norc"]
    }
}
settings["terminal.integrated.inheritEnv"] = False

# Сохраняем обновленные настройки
os.makedirs(os.path.dirname(settings_path), exist_ok=True)
with open(settings_path, 'w', encoding='utf-8') as f:
    json.dump(settings, f, indent=4, ensure_ascii=False)

print(f"\n✓ Настройки терминала Cursor обновлены!")
print("  - Используется bash вместо zsh")
print("  - Отключено наследование переменных окружения")
print("\n⚠️  ПЕРЕЗАПУСТИТЕ CURSOR для применения изменений!")

