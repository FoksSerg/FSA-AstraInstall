#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест универсальной архитектуры компонентов FSA-AstraInstall
Проверяет работу UniversalInstaller и ComponentStatusManager
"""

import sys
import os

# Добавляем путь к основному модулю
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем новые классы
from astra_automation import UniversalInstaller, ComponentStatusManager, COMPONENTS_CONFIG

def test_components_config():
    """Тест конфигурации компонентов"""
    print("=" * 60)
    print("ТЕСТ КОНФИГУРАЦИИ КОМПОНЕНТОВ")
    print("=" * 60)
    
    print(f"Всего компонентов: {len(COMPONENTS_CONFIG)}")
    
    # Группируем по категориям
    categories = {}
    for component_id, config in COMPONENTS_CONFIG.items():
        category = config['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(component_id)
    
    print("\nКомпоненты по категориям:")
    for category, components in categories.items():
        print(f"  {category}: {len(components)} компонентов")
        for component_id in components:
            config = COMPONENTS_CONFIG[component_id]
            print(f"    - {config['name']} (приоритет: {config['priority']})")
    
    # Проверяем зависимости
    print("\nПроверка зависимостей:")
    for component_id, config in COMPONENTS_CONFIG.items():
        deps = config['dependencies']
        if deps:
            print(f"  {config['name']} зависит от: {', '.join(deps)}")
    
    return True

def test_universal_installer():
    """Тест универсального установщика"""
    print("\n" + "=" * 60)
    print("ТЕСТ УНИВЕРСАЛЬНОГО УСТАНОВЩИКА")
    print("=" * 60)
    
    # Создаем установщик
    installer = UniversalInstaller()
    
    # Тест разрешения зависимостей
    test_components = ['astra_ide', 'wine_9']
    print(f"Тестируем разрешение зависимостей для: {test_components}")
    
    resolved = installer.resolve_dependencies(test_components)
    print(f"Результат: {resolved}")
    
    # Тест поиска детей
    test_parents = ['wineprefix']
    print(f"\nТестируем поиск детей для: {test_parents}")
    
    children = installer.find_all_children(test_parents)
    print(f"Дети: {children}")
    
    # Тест проверки статуса
    print(f"\nТестируем проверку статуса компонентов:")
    for component_id in ['wine_astraregul', 'wineprefix', 'astra_ide']:
        status = installer.check_component_status(component_id)
        print(f"  {component_id}: {'установлен' if status else 'не установлен'}")
    
    return True

def test_status_manager():
    """Тест менеджера статусов"""
    print("\n" + "=" * 60)
    print("ТЕСТ МЕНЕДЖЕРА СТАТУСОВ")
    print("=" * 60)
    
    # Создаем менеджер статусов
    status_manager = ComponentStatusManager()
    
    # Тест получения статуса всех компонентов
    all_status = status_manager.get_all_components_status()
    print(f"Статус всех компонентов получен: {len(all_status)} компонентов")
    
    # Тест получения компонентов по категориям
    categories = ['wine_packages', 'winetricks', 'application']
    for category in categories:
        components = status_manager.get_components_by_category(category)
        print(f"  {category}: {len(components)} компонентов")
    
    # Тест получения выбираемых компонентов
    selectable = status_manager.get_selectable_components()
    print(f"\nВыбираемые компоненты: {len(selectable)}")
    for component_id in selectable:
        config = COMPONENTS_CONFIG[component_id]
        print(f"  - {config['name']}")
    
    # Тест прогресса установки
    progress = status_manager.get_installation_progress()
    print(f"\nПрогресс установки:")
    print(f"  Всего: {progress['total']}")
    print(f"  Установлено: {progress['installed']}")
    print(f"  Отсутствует: {progress['missing']}")
    print(f"  Прогресс: {progress['progress_percent']:.1f}%")
    
    # Тест валидации зависимостей
    test_components = ['astra_ide', 'wineprefix']
    validation = status_manager.validate_dependencies(test_components)
    print(f"\nВалидация зависимостей для {test_components}:")
    print(f"  Валидно: {validation['valid']}")
    if validation['missing_dependencies']:
        print(f"  Отсутствующие зависимости: {validation['missing_dependencies']}")
    if validation['circular_dependencies']:
        print(f"  Циклические зависимости: {validation['circular_dependencies']}")
    
    return True

def test_integration():
    """Тест интеграции компонентов"""
    print("\n" + "=" * 60)
    print("ТЕСТ ИНТЕГРАЦИИ")
    print("=" * 60)
    
    # Создаем оба менеджера
    installer = UniversalInstaller()
    status_manager = ComponentStatusManager()
    
    # Тест синхронизации статусов
    print("Тестируем синхронизацию статусов...")
    
    # Получаем статус через оба менеджера
    component_id = 'wine_astraregul'
    installer_status = installer.check_component_status(component_id)
    status_manager_status = status_manager.check_component_status(component_id)
    
    print(f"Статус {component_id}:")
    print(f"  UniversalInstaller: {'установлен' if installer_status else 'не установлен'}")
    print(f"  ComponentStatusManager: {'установлен' if status_manager_status else 'не установлен'}")
    print(f"  Синхронизированы: {installer_status == status_manager_status}")
    
    # Тест обновления статуса
    print(f"\nТестируем обновление статуса...")
    status_manager.update_component_status(component_id, 'pending')
    status_text, status_tag = status_manager.get_component_status(component_id, COMPONENTS_CONFIG[component_id]['name'])
    print(f"Статус после обновления: {status_text} ({status_tag})")
    
    return True

def main():
    """Главная функция тестирования"""
    print("FSA-AstraInstall - Тест универсальной архитектуры компонентов")
    print("Версия: 1.0")
    
    try:
        # Запускаем тесты
        test_components_config()
        test_universal_installer()
        test_status_manager()
        test_integration()
        
        print("\n" + "=" * 60)
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\nОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
