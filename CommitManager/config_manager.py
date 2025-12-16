#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер конфигураций для CommitManager
Версия: V3.4.184 (2025.12.16)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
from .project_config import ProjectConfig


class ConfigManager:
    """Менеджер конфигураций проектов"""
    
    def __init__(self, config_file_path: Optional[str] = None):
        """
        Инициализация менеджера конфигураций
        
        Args:
            config_file_path: Путь к файлу конфигурации. Если None, используется по умолчанию
        """
        if config_file_path is None:
            # Используем директорию модуля CommitManager
            commit_manager_dir = os.path.dirname(os.path.abspath(__file__))
            config_file_path = os.path.join(commit_manager_dir, 'config.json')
        
        self.config_file_path = config_file_path
        self.config = {}
        self._load()
    
    def _get_project_dir(self) -> str:
        """Получить директорию проекта"""
        # Получаем родительскую директорию модуля CommitManager
        commit_manager_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(commit_manager_dir)
        
        # Проверяем наличие .git в родительской директории
        if os.path.exists(os.path.join(parent_dir, '.git')):
            return parent_dir
        
        # Иначе возвращаем родительскую директорию
        return parent_dir
    
    def _load(self):
        """Загрузка конфигурации из файла"""
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ConfigManager] Ошибка загрузки конфига: {e}")
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Возвращает конфигурацию по умолчанию"""
        return {
            'version': '1.0.0',
            'last_updated': datetime.now().isoformat(),
            'projects': {},
            'current_project': None,
            'ui': {
                'window_width': 1400,
                'window_height': 900,
                'theme': 'default'
            }
        }
    
    def save(self) -> bool:
        """Сохранение конфигурации в файл"""
        try:
            # Обновляем время последнего изменения
            self.config['last_updated'] = datetime.now().isoformat()
            
            # Создаём директорию если не существует
            config_dir = os.path.dirname(self.config_file_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # Сохраняем в файл
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"[ConfigManager] Ошибка сохранения конфига: {e}")
            return False
    
    def get_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Получить конфигурацию проекта"""
        projects = self.config.get('projects', {})
        if project_name in projects:
            return ProjectConfig(projects[project_name])
        return None
    
    def set_project_config(self, project_name: str, config: ProjectConfig):
        """Сохранить конфигурацию проекта"""
        if 'projects' not in self.config:
            self.config['projects'] = {}
        
        self.config['projects'][project_name] = config.to_dict()
        self.save()
    
    def get_all_projects(self) -> List[str]:
        """Получить список всех проектов"""
        return list(self.config.get('projects', {}).keys())
    
    def get_current_project(self) -> Optional[str]:
        """Получить текущий выбранный проект"""
        return self.config.get('current_project')
    
    def set_current_project(self, project_name: str):
        """Установить текущий проект"""
        self.config['current_project'] = project_name
        self.save()
    
    def delete_project(self, project_name: str) -> bool:
        """Удалить проект из конфигурации"""
        if project_name in self.config.get('projects', {}):
            del self.config['projects'][project_name]
            
            # Если удаляемый проект был текущим, сбрасываем текущий проект
            if self.config.get('current_project') == project_name:
                self.config['current_project'] = None
            
            self.save()
            return True
        return False
    
    def get_ui_config(self) -> Dict:
        """Получить настройки UI"""
        return self.config.get('ui', {
            'window_width': 1400,
            'window_height': 900,
            'window_x': None,
            'window_y': None,
            'window_geometry': None,
            'paned_positions': {},
            'theme': 'default'
        })
    
    def set_ui_config(self, ui_config: Dict):
        """Установить настройки UI"""
        if 'ui' not in self.config:
            self.config['ui'] = {}
        self.config['ui'].update(ui_config)
        self.save()
    
    def save_window_geometry(self, geometry: str, paned_positions: Optional[Dict[str, int]] = None):
        """Сохранить геометрию окна и позиции разделителей"""
        try:
            # Парсим геометрию: "widthxheight+x+y"
            if '+' in geometry:
                size_pos = geometry.split('+')
                size = size_pos[0]
                x = int(size_pos[1])
                y = int(size_pos[2])
                width, height = map(int, size.split('x'))
            else:
                # Только размер без позиции
                width, height = map(int, geometry.split('x'))
                x = None
                y = None
            
            ui_config = {
                'window_geometry': geometry,
                'window_width': width,
                'window_height': height,
                'window_x': x,
                'window_y': y
            }
            
            if paned_positions:
                ui_config['paned_positions'] = paned_positions
            
            self.set_ui_config(ui_config)
        except Exception as e:
            print(f"[ConfigManager] Ошибка сохранения геометрии: {e}")
    
    def get_window_geometry(self) -> Optional[str]:
        """Получить сохраненную геометрию окна"""
        ui_config = self.get_ui_config()
        return ui_config.get('window_geometry')
    
    def get_paned_positions(self) -> Dict[str, int]:
        """Получить сохраненные позиции разделителей"""
        ui_config = self.get_ui_config()
        return ui_config.get('paned_positions', {})
    
    def create_default_fsa_config(self) -> ProjectConfig:
        """Создать конфигурацию по умолчанию для FSA-AstraInstall"""
        project_path = self._get_project_dir()
        
        default_config = {
            'name': 'FSA-AstraInstall',
            'path': project_path,
            'version_file': 'Version.txt',
            'version_format': 'V{MAJOR}.{MINOR}.{PATCH}',
            'key_files': [
                'FSA-AstraInstall.py',
                'README.md',
                'Version.txt',
                'DocInstruction/WINE_INSTALL_GUIDE.md'
            ],
            'binary_files': [
                {
                    'name': 'FSA-AstraInstall-1-7',
                    'build_command': 'python3 RunScript/docker_build_all.py',
                    'auto_rebuild': True
                },
                {
                    'name': 'FSA-AstraInstall-1-8',
                    'build_command': 'python3 RunScript/docker_build_all.py',
                    'auto_rebuild': True
                }
            ],
            'history': {
                'enabled': True,
                'files': [
                    'FSA-AstraInstall.py',
                    'FSA-AstraInstall-1-7',
                    'FSA-AstraInstall-1-8'
                ],
                'directory': 'History',
                'folder_format': '{date}',
                'max_snapshots': 100,
                'auto_cleanup': True,
                'create_on_key_files_change': True
            },
            'versioning': {
                'update_key_files': True,
                'update_release_date': True,
                'file_extensions': ['.py', '.sh', '.md'],
                'version_template': 'Версия проекта: {version}',
                'date_template': 'Дата релиза: {date}'
            },
            'commit': {
                'ask_permission': True,
                'show_file_list': True,
                'message_template': 'Проект: {project}\nДата: {date}'
            },
            'ai_analysis': {
                'method': 'hybrid',
                'provider': 'openai',
                'api_key': '',
                'model': 'gpt-4-turbo-preview',
                'temperature': 0.7,
                'max_tokens': 2000,
                'prompt_template': 'Проанализируй изменения в файлах проекта и создай краткое описание коммита на русском языке.'
            }
        }
        
        return ProjectConfig(default_config)
