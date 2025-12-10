#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки доступности спецсимволов на Astra Linux 1.7
Версия: V3.4.174
Дата: 2025.12.11
Компания: ООО "НПА Вира-Реалтайм"

Цель: Определить, какие Unicode символы можно использовать вместо эмодзи
      для совместимости с Astra Linux 1.7
"""

import sys
import os
import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime

# Категории символов для тестирования
SYMBOL_CATEGORIES = {
    'Стрелки': [
        ('→', 'U+2192', 'RIGHTWARDS ARROW'),
        ('←', 'U+2190', 'LEFTWARDS ARROW'),
        ('↑', 'U+2191', 'UPWARDS ARROW'),
        ('↓', 'U+2193', 'DOWNWARDS ARROW'),
        ('↔', 'U+2194', 'LEFT RIGHT ARROW'),
        ('⇒', 'U+21D2', 'RIGHTWARDS DOUBLE ARROW'),
        ('⇐', 'U+21D0', 'LEFTWARDS DOUBLE ARROW'),
        ('⇑', 'U+21D1', 'UPWARDS DOUBLE ARROW'),
        ('⇓', 'U+21D3', 'DOWNWARDS DOUBLE ARROW'),
        ('▶', 'U+25B6', 'BLACK RIGHT-POINTING TRIANGLE'),
        ('◀', 'U+25C0', 'BLACK LEFT-POINTING TRIANGLE'),
        ('▼', 'U+25BC', 'BLACK DOWN-POINTING TRIANGLE'),
        ('▲', 'U+25B2', 'BLACK UP-POINTING TRIANGLE'),
        ('►', 'U+25BA', 'BLACK RIGHT-POINTING SMALL TRIANGLE'),
        ('◄', 'U+25C4', 'BLACK LEFT-POINTING SMALL TRIANGLE'),
    ],
    'Геометрические фигуры': [
        ('●', 'U+25CF', 'BLACK CIRCLE'),
        ('○', 'U+25CB', 'WHITE CIRCLE'),
        ('■', 'U+25A0', 'BLACK SQUARE'),
        ('□', 'U+25A1', 'WHITE SQUARE'),
        ('◆', 'U+25C6', 'BLACK DIAMOND'),
        ('◇', 'U+25C7', 'WHITE DIAMOND'),
        ('★', 'U+2605', 'BLACK STAR'),
        ('☆', 'U+2606', 'WHITE STAR'),
        ('▪', 'U+25AA', 'BLACK SMALL SQUARE'),
        ('▫', 'U+25AB', 'WHITE SMALL SQUARE'),
        ('▸', 'U+25B8', 'BLACK RIGHT-POINTING SMALL TRIANGLE'),
        ('▹', 'U+25B9', 'WHITE RIGHT-POINTING SMALL TRIANGLE'),
    ],
    'Математические и технические': [
        ('✓', 'U+2713', 'CHECK MARK'),
        ('✗', 'U+2717', 'BALLOT X'),
        ('✘', 'U+2718', 'HEAVY BALLOT X'),
        ('✕', 'U+2715', 'MULTIPLICATION X'),
        ('✖', 'U+2716', 'HEAVY MULTIPLICATION X'),
        ('✚', 'U+271A', 'HEAVY GREEK CROSS'),
        ('✛', 'U+271B', 'OPEN CENTRE CROSS'),
        ('✜', 'U+271C', 'HEAVY OPEN CENTRE CROSS'),
        ('✝', 'U+271D', 'LATIN CROSS'),
        ('✞', 'U+271E', 'SHADOWED WHITE LATIN CROSS'),
        ('✟', 'U+271F', 'OUTLINED LATIN CROSS'),
        ('±', 'U+00B1', 'PLUS-MINUS SIGN'),
        ('×', 'U+00D7', 'MULTIPLICATION SIGN'),
        ('÷', 'U+00F7', 'DIVISION SIGN'),
        ('≈', 'U+2248', 'ALMOST EQUAL TO'),
        ('≠', 'U+2260', 'NOT EQUAL TO'),
        ('≤', 'U+2264', 'LESS-THAN OR EQUAL TO'),
        ('≥', 'U+2265', 'GREATER-THAN OR EQUAL TO'),
    ],
    'Буквенные символы': [
        ('©', 'U+00A9', 'COPYRIGHT SIGN'),
        ('®', 'U+00AE', 'REGISTERED SIGN'),
        ('™', 'U+2122', 'TRADE MARK SIGN'),
        ('℠', 'U+2120', 'SERVICE MARK'),
        ('°', 'U+00B0', 'DEGREE SIGN'),
        ('§', 'U+00A7', 'SECTION SIGN'),
        ('¶', 'U+00B6', 'PILCROW SIGN'),
        ('†', 'U+2020', 'DAGGER'),
        ('‡', 'U+2021', 'DOUBLE DAGGER'),
        ('•', 'U+2022', 'BULLET'),
        ('…', 'U+2026', 'HORIZONTAL ELLIPSIS'),
    ],
    'Символы валют': [
        ('€', 'U+20AC', 'EURO SIGN'),
        ('£', 'U+00A3', 'POUND SIGN'),
        ('¥', 'U+00A5', 'YEN SIGN'),
        ('¢', 'U+00A2', 'CENT SIGN'),
        ('¤', 'U+00A4', 'CURRENCY SIGN'),
    ],
    'Боксы и рамки': [
        ('┌', 'U+250C', 'BOX DRAWINGS LIGHT DOWN AND RIGHT'),
        ('┐', 'U+2510', 'BOX DRAWINGS LIGHT DOWN AND LEFT'),
        ('└', 'U+2514', 'BOX DRAWINGS LIGHT UP AND RIGHT'),
        ('┘', 'U+2518', 'BOX DRAWINGS LIGHT UP AND LEFT'),
        ('├', 'U+251C', 'BOX DRAWINGS LIGHT VERTICAL AND RIGHT'),
        ('┤', 'U+2524', 'BOX DRAWINGS LIGHT VERTICAL AND LEFT'),
        ('┬', 'U+252C', 'BOX DRAWINGS LIGHT DOWN AND HORIZONTAL'),
        ('┴', 'U+2534', 'BOX DRAWINGS LIGHT UP AND HORIZONTAL'),
        ('─', 'U+2500', 'BOX DRAWINGS LIGHT HORIZONTAL'),
        ('│', 'U+2502', 'BOX DRAWINGS LIGHT VERTICAL'),
        ('═', 'U+2550', 'BOX DRAWINGS DOUBLE HORIZONTAL'),
        ('║', 'U+2551', 'BOX DRAWINGS DOUBLE VERTICAL'),
    ],
    'Технические символы': [
        ('⚙', 'U+2699', 'GEAR'),
        ('⚡', 'U+26A1', 'HIGH VOLTAGE SIGN'),
        ('⚠', 'U+26A0', 'WARNING SIGN'),
        ('⚛', 'U+269B', 'ATOM SYMBOL'),
        ('⚜', 'U+269C', 'FLEUR-DE-LIS'),
    ],
    'Эмодзи (для сравнения - должны не работать)': [
        ('📁', 'U+1F4C1', 'FOLDER'),
        ('📄', 'U+1F4C4', 'PAGE FACING UP'),
        ('📸', 'U+1F4F8', 'CAMERA'),
        ('🔧', 'U+1F527', 'WRENCH'),
        ('📊', 'U+1F4CA', 'BAR CHART'),
        ('📈', 'U+1F4C8', 'CHART WITH UPWARDS TREND'),
        ('📉', 'U+1F4C9', 'CHART WITH DOWNWARDS TREND'),
        ('✅', 'U+2705', 'WHITE HEAVY CHECK MARK'),
        ('❌', 'U+274C', 'CROSS MARK'),
    ],
}

class SymbolTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Тест символов для Astra Linux 1.7")
        self.root.geometry("1000x700")
        
        # Результаты тестирования
        self.results = {}
        
        self.create_ui()
    
    def create_ui(self):
        """Создание интерфейса"""
        # Заголовок
        header = tk.Label(
            self.root,
            text="Тест доступности Unicode символов для Astra Linux 1.7",
            font=('Arial', 12, 'bold')
        )
        header.pack(pady=10)
        
        # Информация о системе
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            info_frame,
            text=f"Python: {sys.version.split()[0]}",
            font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            info_frame,
            text=f"Платформа: {sys.platform}",
            font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)
        
        # Notebook для категорий
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Создаём вкладки для каждой категории
        for category, symbols in SYMBOL_CATEGORIES.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=category)
            
            # Таблица результатов
            tree = ttk.Treeview(
                frame,
                columns=('symbol', 'unicode', 'name', 'status', 'width'),
                show='headings',
                height=20
            )
            
            tree.heading('symbol', text='Символ')
            tree.heading('unicode', text='Unicode')
            tree.heading('name', text='Название')
            tree.heading('status', text='Статус')
            tree.heading('width', text='Ширина (px)')
            
            tree.column('symbol', width=100, anchor='center')
            tree.column('unicode', width=100, anchor='center')
            tree.column('name', width=350)
            tree.column('status', width=150, anchor='center')
            tree.column('width', width=100, anchor='center')
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Тестируем символы
            for symbol, unicode_code, name in symbols:
                try:
                    # Пробуем отобразить символ
                    test_label = tk.Label(self.root, text=symbol, font=('Arial', 12))
                    test_label.update()
                    width_pixels = test_label.winfo_reqwidth()
                    test_label.destroy()
                    
                    # Если символ отображается как квадратик или имеет необычную ширину - не работает
                    # Нормальная ширина символа обычно 8-20 пикселей для Arial 12
                    if width_pixels < 5 or width_pixels > 50:
                        status = '✗ Не работает'
                        tag = 'error'
                    else:
                        status = '✓ Работает'
                        tag = 'ok'
                    
                    item = tree.insert('', 'end', values=(symbol, unicode_code, name, status, f'{width_pixels}px'), tags=(tag,))
                    
                    # Цветовая подсветка
                    if tag == 'ok':
                        tree.set(item, 'status', status)
                    else:
                        tree.set(item, 'status', status)
                    
                    # Сохраняем результат
                    self.results[f"{category}_{symbol}"] = {
                        'symbol': symbol,
                        'unicode': unicode_code,
                        'name': name,
                        'status': status,
                        'width': width_pixels,
                        'category': category
                    }
                except Exception as e:
                    status = f'✗ Ошибка: {str(e)[:30]}'
                    item = tree.insert('', 'end', values=(symbol, unicode_code, name, status, 'N/A'), tags=('error',))
                    self.results[f"{category}_{symbol}"] = {
                        'symbol': symbol,
                        'unicode': unicode_code,
                        'name': name,
                        'status': status,
                        'width': None,
                        'category': category,
                        'error': str(e)
                    }
            
            # Настройка тегов для цветовой подсветки
            tree.tag_configure('ok', foreground='green')
            tree.tag_configure('error', foreground='red')
        
        # Кнопки управления
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            button_frame,
            text="Сохранить результаты в JSON",
            command=self.save_results
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="Создать таблицу замены",
            command=self.create_replacement_table
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="Показать статистику",
            command=self.show_statistics
        ).pack(side=tk.LEFT, padx=5)
    
    def save_results(self):
        """Сохранение результатов в файл"""
        filename = f"symbol_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            # Показываем сообщение
            msg = tk.Toplevel(self.root)
            msg.title("Результаты сохранены")
            msg.geometry("300x100")
            tk.Label(msg, text=f"Результаты сохранены в:\n{filename}", font=('Arial', 10)).pack(pady=20)
            tk.Button(msg, text="OK", command=msg.destroy).pack()
            
            print(f"Результаты сохранены в {filename}")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
    
    def create_replacement_table(self):
        """Создание таблицы замены эмодзи на спецсимволы"""
        # Фильтруем только рабочие символы
        working_symbols = {k: v for k, v in self.results.items() if '✓ Работает' in v.get('status', '')}
        
        # Создаём таблицу замены
        replacements = []
        
        # Эмодзи для замены
        emoji_to_replace = {
            '📁': 'FOLDER',
            '📄': 'PAGE',
            '📸': 'CAMERA',
            '🔧': 'WRENCH',
        }
        
        # Ищем подходящие замены
        for emoji, emoji_name in emoji_to_replace.items():
            # Ищем похожие символы
            possible_replacements = []
            for key, data in working_symbols.items():
                symbol = data['symbol']
                name = data['name'].upper()
                if any(word in name for word in ['CIRCLE', 'SQUARE', 'DIAMOND', 'TRIANGLE', 'STAR']):
                    possible_replacements.append((symbol, data['unicode'], data['name']))
            
            replacements.append({
                'emoji': emoji,
                'emoji_name': emoji_name,
                'replacements': possible_replacements[:3]  # Топ-3 варианта
            })
        
        # Сохраняем таблицу
        filename = "emoji_replacement_table.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Таблица замены эмодзи на спецсимволы для Astra Linux 1.7\n")
                f.write("=" * 70 + "\n\n")
                
                f.write("РАБОЧИЕ СИМВОЛЫ:\n")
                f.write("-" * 70 + "\n")
                for key, data in sorted(working_symbols.items()):
                    f.write(f"{data['symbol']} ({data['unicode']}) - {data['name']}\n")
                
                f.write("\n\nРЕКОМЕНДУЕМЫЕ ЗАМЕНЫ:\n")
                f.write("-" * 70 + "\n")
                f.write("📁 → [DIR] или ● (чёрный круг)\n")
                f.write("📄 → [FILE] или ■ (чёрный квадрат)\n")
                f.write("📸 → [IMG] или ◆ (чёрный ромб)\n")
                f.write("🔧 → [CFG] или ⚙ (шестерёнка, если работает)\n")
            
            msg = tk.Toplevel(self.root)
            msg.title("Таблица создана")
            msg.geometry("300x100")
            tk.Label(msg, text=f"Таблица сохранена в:\n{filename}", font=('Arial', 10)).pack(pady=20)
            tk.Button(msg, text="OK", command=msg.destroy).pack()
            
            print(f"Таблица замены сохранена в {filename}")
        except Exception as e:
            print(f"Ошибка создания таблицы: {e}")
    
    def show_statistics(self):
        """Показать статистику тестирования"""
        total = len(self.results)
        working = sum(1 for v in self.results.values() if '✓ Работает' in v.get('status', ''))
        not_working = total - working
        
        stats = f"""Статистика тестирования:

Всего символов: {total}
✓ Работает: {working} ({working*100//total}%)
✗ Не работает: {not_working} ({not_working*100//total}%)
"""
        
        msg = tk.Toplevel(self.root)
        msg.title("Статистика")
        msg.geometry("300x150")
        tk.Label(msg, text=stats, font=('Arial', 10), justify='left').pack(pady=20)
        tk.Button(msg, text="OK", command=msg.destroy).pack()

def main():
    root = tk.Tk()
    app = SymbolTester(root)
    root.mainloop()

if __name__ == '__main__':
    main()
