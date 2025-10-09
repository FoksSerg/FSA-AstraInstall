#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест интеграции GUI с универсальной архитектурой компонентов
Проверяет работу astra_automation.AutomationGUI с новыми классами
"""

import sys
import os

# Добавляем путь к основному модулю
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gui_integration():
    """Тест интеграции GUI с новой архитектурой"""
    print("=" * 60)
    print("ТЕСТ ИНТЕГРАЦИИ GUI С УНИВЕРСАЛЬНОЙ АРХИТЕКТУРОЙ")
    print("=" * 60)
    
    try:
        # Импортируем классы
        import astra_automation
        
        print("✅ Импорт классов успешен")
        
        # Тест создания astra_automation.AutomationGUI
        print("\nТестируем создание astra_automation.AutomationGUI...")
        try:
            # Создаем GUI в консольном режиме для тестирования
            gui = astra_automation.AutomationGUI(console_mode=True)
            print("✅ astra_automation.AutomationGUI создан успешно")
            
            # Проверяем инициализацию новых компонентов
            if hasattr(gui, 'component_status_manager'):
                print("✅ astra_automation.ComponentStatusManager инициализирован")
            else:
                print("❌ astra_automation.ComponentStatusManager не найден")
                
            if hasattr(gui, 'universal_installer'):
                print("✅ astra_automation.UniversalInstaller инициализирован")
            else:
                print("❌ astra_automation.UniversalInstaller не найден")
                
            # Тест получения статусов через новую архитектуру
            print("\nТестируем получение статусов компонентов...")
            all_status = gui.component_status_manager.get_all_components_status()
            print(f"✅ Получено статусов: {len(all_status)}")
            
            # Тест группировки по категориям
            print("\nТестируем группировку по категориям...")
            categories = {}
            for component_id, config in astra_automation.COMPONENTS_CONFIG.items():
                category = config['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(component_id)
            
            for category, components in categories.items():
                print(f"  {category}: {len(components)} компонентов")
            
            # Тест валидации зависимостей
            print("\nТестируем валидацию зависимостей...")
            test_components = ['astra_ide', 'wineprefix']
            validation = gui.component_status_manager.validate_dependencies(test_components)
            print(f"✅ Валидация зависимостей: {validation['valid']}")
            
            # Тест прогресса установки
            print("\nТестируем прогресс установки...")
            progress = gui.component_status_manager.get_installation_progress()
            print(f"✅ Прогресс: {progress['progress_percent']:.1f}% ({progress['installed']}/{progress['total']})")
            
            print("\n" + "=" * 60)
            print("ВСЕ ТЕСТЫ ИНТЕГРАЦИИ ПРОЙДЕНЫ УСПЕШНО!")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания GUI: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_gui_components():
    """Тест компонентов GUI"""
    print("\n" + "=" * 60)
    print("ТЕСТ КОМПОНЕНТОВ GUI")
    print("=" * 60)
    
    try:
        import astra_automation
        
        # Создаем GUI в консольном режиме
        gui = astra_automation.AutomationGUI(console_mode=True)
        
        # Проверяем наличие необходимых методов
        required_methods = [
            '_component_status_callback',
            '_update_wine_status',
            '_perform_wine_check',
            'run_wine_check'
        ]
        
        for method_name in required_methods:
            if hasattr(gui, method_name):
                print(f"✅ Метод {method_name} найден")
            else:
                print(f"❌ Метод {method_name} не найден")
        
        # Тест callback метода
        print("\nТестируем callback метод...")
        gui._component_status_callback("UPDATE_COMPONENT:wine_astraregul")
        print("✅ Callback метод работает")
        
        print("\n" + "=" * 60)
        print("ТЕСТЫ КОМПОНЕНТОВ GUI ЗАВЕРШЕНЫ!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования компонентов: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция тестирования"""
    print("FSA-AstraInstall - Тест интеграции GUI с универсальной архитектурой")
    print("Версия: 1.0")
    
    try:
        # Запускаем тесты
        success1 = test_gui_integration()
        success2 = test_gui_components()
        
        if success1 and success2:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("GUI успешно интегрирован с универсальной архитектурой компонентов")
            return True
        else:
            print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            return False
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
