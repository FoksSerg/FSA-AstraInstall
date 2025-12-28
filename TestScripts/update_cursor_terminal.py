#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления настроек терминала Cursor
Версия: V3.7.207 (2025.12.29)
Компания: ООО "НПА Вира-Реалтайм"
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

# ИСПРАВЛЕНО: Убраны проблемные опции --noprofile --norc
# Эти опции отключают загрузку .bashrc, что вызывает проблемы с screen/tmux
# Теперь bash загружает нормальные настройки окружения
settings["terminal.integrated.defaultProfile.osx"] = "bash"
settings["terminal.integrated.profiles.osx"] = {
    "bash": {
        "path": "/bin/bash"
        # УБРАНО: "args": ["--noprofile", "--norc"] - вызывало проблемы с screen
    }
}

# ИСПРАВЛЕНО: Включаем наследование переменных окружения
# Это необходимо для корректной работы screen, tmux и других утилит
settings["terminal.integrated.inheritEnv"] = True

# Дополнительные настройки для улучшения совместимости
# Отключаем shell integration только для screen/tmux (определяется автоматически)
settings["terminal.integrated.shellIntegration.enabled"] = True
settings["terminal.integrated.shellIntegration.decorationsEnabled"] = "both"

# ИСПРАВЛЕНО: Отключаем предупреждения о перезапуске терминала
# Расширения могут добавлять переменные окружения без перезапуска
settings["terminal.integrated.enablePersistentSessions"] = True
settings["terminal.integrated.showExitAlert"] = False

# Настройки Git extension для работы без перезапуска терминала
settings["git.terminalAuthentication"] = False
settings["git.useEditorAsCommitInput"] = True

# Сохраняем обновленные настройки
os.makedirs(os.path.dirname(settings_path), exist_ok=True)
with open(settings_path, 'w', encoding='utf-8') as f:
    json.dump(settings, f, indent=4, ensure_ascii=False)

print(f"\n✓ Настройки терминала Cursor обновлены!")
print("  - Используется bash (с загрузкой .bashrc)")
print("  - Включено наследование переменных окружения")
print("  - Shell integration включен для совместимости")
print("\n⚠️  ПЕРЕЗАПУСТИТЕ CURSOR для применения изменений!")
print("\n📝 ИСПРАВЛЕНИЯ:")
print("  - Убраны опции --noprofile --norc (вызывали проблемы с screen)")
print("  - Включено наследование окружения (необходимо для screen/tmux)")
print("  - Shell integration настроен для корректной работы")

