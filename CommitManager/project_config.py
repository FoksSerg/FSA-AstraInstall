#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Класс конфигурации проекта для CommitManager
Версия: V3.4.184 (2025.12.16)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
from typing import List, Dict, Optional
from pathlib import Path


class ProjectConfig:
    """Класс конфигурации проекта для создания коммитов"""
    
    def __init__(self, config_data: Dict):
        """
        Инициализация конфигурации проекта
        
        Args:
            config_data: Словарь с данными конфигурации
        """
        self.name = config_data.get('name', '')
        self.path = config_data.get('path', '')
        self.version_file = config_data.get('version_file', 'Version.txt')
        self.version_format = config_data.get('version_format', 'V{MAJOR}.{MINOR}.{PATCH}')
        
        # Ключевые файлы
        self.key_files = config_data.get('key_files', [])
        
        # Бинарные файлы
        self.binary_files = config_data.get('binary_files', [])
        
        # Настройки истории
        history_config = config_data.get('history', {})
        self.history_enabled = history_config.get('enabled', True)
        self.history_files = history_config.get('files', [])
        self.history_directory = history_config.get('directory', 'History')
        self.history_folder_format = history_config.get('folder_format', '{date}')
        self.history_max_snapshots = history_config.get('max_snapshots', 100)
        self.history_auto_cleanup = history_config.get('auto_cleanup', True)
        self.history_create_on_key_files_change = history_config.get('create_on_key_files_change', True)
        
        # Настройки версионирования
        versioning_config = config_data.get('versioning', {})
        self.update_key_files = versioning_config.get('update_key_files', True)
        self.update_release_date = versioning_config.get('update_release_date', True)
        self.file_extensions = versioning_config.get('file_extensions', ['.py', '.sh', '.md'])
        self.version_template = versioning_config.get('version_template', 'Версия проекта: {version}')
        self.date_template = versioning_config.get('date_template', 'Дата релиза: {date}')
        
        # Настройки коммита
        commit_config = config_data.get('commit', {})
        self.ask_permission = commit_config.get('ask_permission', True)
        self.show_file_list = commit_config.get('show_file_list', True)
        self.message_template = commit_config.get('message_template', 'Проект: {project}\nДата: {date}')
        
        # Настройки AI анализа
        ai_config = config_data.get('ai_analysis', {})
        self.ai_method = ai_config.get('method', 'hybrid')  # 'api', 'hybrid', 'local', 'manual'
        self.ai_provider = ai_config.get('provider', 'openai')
        self.ai_api_key = ai_config.get('api_key', '')
        self.ai_model = ai_config.get('model', 'gpt-4-turbo-preview')
        self.ai_temperature = ai_config.get('temperature', 0.7)
        self.ai_max_tokens = ai_config.get('max_tokens', 2000)
        self.ai_prompt_template = ai_config.get('prompt_template', '')
    
    def to_dict(self) -> Dict:
        """Преобразовать конфигурацию в словарь"""
        return {
            'name': self.name,
            'path': self.path,
            'version_file': self.version_file,
            'version_format': self.version_format,
            'key_files': self.key_files,
            'binary_files': self.binary_files,
            'history': {
                'enabled': self.history_enabled,
                'files': self.history_files,
                'directory': self.history_directory,
                'folder_format': self.history_folder_format,
                'max_snapshots': self.history_max_snapshots,
                'auto_cleanup': self.history_auto_cleanup,
                'create_on_key_files_change': self.history_create_on_key_files_change
            },
            'versioning': {
                'update_key_files': self.update_key_files,
                'update_release_date': self.update_release_date,
                'file_extensions': self.file_extensions,
                'version_template': self.version_template,
                'date_template': self.date_template
            },
            'commit': {
                'ask_permission': self.ask_permission,
                'show_file_list': self.show_file_list,
                'message_template': self.message_template
            },
            'ai_analysis': {
                'method': self.ai_method,
                'provider': self.ai_provider,
                'api_key': self.ai_api_key,
                'model': self.ai_model,
                'temperature': self.ai_temperature,
                'max_tokens': self.ai_max_tokens,
                'prompt_template': self.ai_prompt_template
            }
        }
    
    def get_version_file_path(self) -> str:
        """Получить полный путь к файлу версии"""
        return os.path.join(self.path, self.version_file)
    
    def get_key_file_paths(self) -> List[str]:
        """Получить полные пути к ключевым файлам"""
        return [os.path.join(self.path, f) for f in self.key_files if f]
    
    def get_history_directory_path(self) -> str:
        """Получить полный путь к директории истории"""
        return os.path.join(self.path, self.history_directory)
    
    def validate(self) -> tuple[bool, str]:
        """
        Валидация конфигурации
        
        Returns:
            (is_valid, error_message)
        """
        if not self.name:
            return False, "Название проекта не указано"
        
        if not self.path:
            return False, "Путь к проекту не указан"
        
        if not os.path.exists(self.path):
            return False, f"Директория проекта не существует: {self.path}"
        
        if not os.path.isdir(self.path):
            return False, f"Указанный путь не является директорией: {self.path}"
        
        # Проверка файла версии
        version_file_path = self.get_version_file_path()
        if not os.path.exists(version_file_path):
            return False, f"Файл версии не найден: {version_file_path}"
        
        return True, ""
