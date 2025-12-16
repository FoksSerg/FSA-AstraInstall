#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CommitManager - Универсальный инструмент для создания коммитов
Версия: V3.4.184 (2025.12.16)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

__version__ = "V3.4.184 (2025.12.16)"

from .config_manager import ConfigManager
from .project_config import ProjectConfig
from .commit_executor import CommitExecutor
from .commit_analyzer import CommitAnalyzer
from .commit_gui import CommitManagerGUI

__all__ = [
    'ConfigManager',
    'ProjectConfig',
    'CommitExecutor',
    'CommitAnalyzer',
    'CommitManagerGUI'
]
