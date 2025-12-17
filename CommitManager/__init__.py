#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CommitManager - Универсальный инструмент для создания коммитов
Версия: V3.4.186 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

__version__ = "V3.4.186 (2025.12.17)"

from .config_manager import ConfigManager
from .project_config import ProjectConfig
from .commit_executor import CommitExecutor
from .commit_analyzer import CommitAnalyzer
from .commit_gui import CommitManagerGUI
from .test_environment import TestEnvironment
from .logger import CommitLogger, LoggingOutputCallback

__all__ = [
    'ConfigManager',
    'ProjectConfig',
    'CommitExecutor',
    'CommitAnalyzer',
    'CommitManagerGUI',
    'TestEnvironment',
    'CommitLogger',
    'LoggingOutputCallback'
]
