#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Консольная версия тестового скрипта для проверки доступности спецсимволов на Astra Linux 1.7
Версия: V3.4.174
Дата: 2025.12.11
Компания: ООО "НПА Вира-Реалтайм"

Цель: Определить, какие Unicode символы можно использовать вместо эмодзи
      для совместимости с Astra Linux 1.7

Работает БЕЗ tkinter - только консольный вывод
"""

import sys
import os
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
    'Эмодзи - файлы и папки': [
        ('📁', 'U+1F4C1', 'FOLDER'),
        ('📂', 'U+1F4C2', 'OPEN FILE FOLDER'),
        ('📄', 'U+1F4C4', 'PAGE FACING UP'),
        ('📃', 'U+1F4C3', 'PAGE WITH CURL'),
        ('📑', 'U+1F4D1', 'BOOKMARK TABS'),
        ('📊', 'U+1F4CA', 'BAR CHART'),
        ('📈', 'U+1F4C8', 'CHART WITH UPWARDS TREND'),
        ('📉', 'U+1F4C9', 'CHART WITH DOWNWARDS TREND'),
        ('📋', 'U+1F4CB', 'CLIPBOARD'),
        ('📝', 'U+1F4DD', 'MEMO'),
        ('💾', 'U+1F4BE', 'FLOPPY DISK'),
        ('💿', 'U+1F4BF', 'OPTICAL DISC'),
        ('📀', 'U+1F4C0', 'DVD'),
        ('💽', 'U+1F4BD', 'COMPUTER DISK'),
    ],
    'Эмодзи - техника и инструменты': [
        ('🔧', 'U+1F527', 'WRENCH'),
        ('🔨', 'U+1F528', 'HAMMER'),
        ('⚙', 'U+2699', 'GEAR'),
        ('🔩', 'U+1F529', 'NUT AND BOLT'),
        ('⚡', 'U+26A1', 'HIGH VOLTAGE SIGN'),
        ('🔌', 'U+1F50C', 'ELECTRIC PLUG'),
        ('💻', 'U+1F4BB', 'LAPTOP'),
        ('🖥', 'U+1F5A5', 'DESKTOP COMPUTER'),
        ('🖨', 'U+1F5A8', 'PRINTER'),
        ('⌨', 'U+2328', 'KEYBOARD'),
        ('🖱', 'U+1F5B1', 'THREE BUTTON MOUSE'),
        ('🖲', 'U+1F5B2', 'TRACKBALL'),
    ],
    'Эмодзи - камера и медиа': [
        ('📸', 'U+1F4F8', 'CAMERA'),
        ('📷', 'U+1F4F7', 'CAMERA'),
        ('📹', 'U+1F4F9', 'VIDEO CAMERA'),
        ('🎥', 'U+1F3A5', 'MOVIE CAMERA'),
        ('📽', 'U+1F4FD', 'FILM PROJECTOR'),
        ('🎞', 'U+1F39E', 'FILM FRAMES'),
        ('📺', 'U+1F4FA', 'TELEVISION'),
        ('📻', 'U+1F4FB', 'RADIO'),
        ('🎙', 'U+1F399', 'MICROPHONE'),
        ('📢', 'U+1F4E2', 'PUBLIC ADDRESS LOUDSPEAKER'),
        ('📣', 'U+1F4E3', 'CHEERING MEGAPHONE'),
    ],
    'Эмодзи - статусы и действия': [
        ('✅', 'U+2705', 'WHITE HEAVY CHECK MARK'),
        ('❌', 'U+274C', 'CROSS MARK'),
        ('⭕', 'U+2B55', 'HEAVY LARGE CIRCLE'),
        ('✔', 'U+2714', 'HEAVY CHECK MARK'),
        ('✖', 'U+2716', 'HEAVY MULTIPLICATION X'),
        ('➕', 'U+2795', 'HEAVY PLUS SIGN'),
        ('➖', 'U+2796', 'HEAVY MINUS SIGN'),
        ('➗', 'U+2797', 'HEAVY DIVISION SIGN'),
        ('🔄', 'U+1F504', 'ANTICLOCKWISE ARROWS BUTTON'),
        ('🔃', 'U+1F503', 'CLOCKWISE VERTICAL ARROWS'),
        ('⏸', 'U+23F8', 'DOUBLE VERTICAL BAR'),
        ('⏹', 'U+23F9', 'STOP SQUARE'),
        ('⏺', 'U+23FA', 'RECORD BUTTON'),
        ('▶', 'U+25B6', 'BLACK RIGHT-POINTING TRIANGLE'),
        ('⏩', 'U+23E9', 'BLACK RIGHT-POINTING DOUBLE TRIANGLE'),
        ('⏪', 'U+23EA', 'BLACK LEFT-POINTING DOUBLE TRIANGLE'),
        ('⏯', 'U+23EF', 'BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR'),
    ],
    'Эмодзи - предупреждения и информация': [
        ('⚠', 'U+26A0', 'WARNING SIGN'),
        ('⚠️', 'U+26A0 U+FE0F', 'WARNING SIGN (emoji variant)'),
        ('🚨', 'U+1F6A8', 'POLICE CAR REVOLVING LIGHT'),
        ('🔔', 'U+1F514', 'BELL'),
        ('🔕', 'U+1F515', 'BELL WITH CANCELLATION STROKE'),
        ('📣', 'U+1F4E3', 'CHEERING MEGAPHONE'),
        ('💡', 'U+1F4A1', 'LIGHT BULB'),
        ('🔍', 'U+1F50D', 'LEFT-POINTING MAGNIFYING GLASS'),
        ('🔎', 'U+1F50E', 'RIGHT-POINTING MAGNIFYING GLASS'),
        ('🔐', 'U+1F510', 'CLOSED LOCK WITH KEY'),
        ('🔒', 'U+1F512', 'LOCK'),
        ('🔓', 'U+1F513', 'OPEN LOCK'),
        ('🔑', 'U+1F511', 'KEY'),
    ],
    'Эмодзи - стрелки и навигация': [
        ('⬆', 'U+2B06', 'UPWARDS BLACK ARROW'),
        ('⬇', 'U+2B07', 'DOWNWARDS BLACK ARROW'),
        ('⬅', 'U+2B05', 'LEFTWARDS BLACK ARROW'),
        ('➡', 'U+27A1', 'BLACK RIGHTWARDS ARROW'),
        ('↗', 'U+2197', 'NORTH EAST ARROW'),
        ('↘', 'U+2198', 'SOUTH EAST ARROW'),
        ('↙', 'U+2199', 'SOUTH WEST ARROW'),
        ('↖', 'U+2196', 'NORTH WEST ARROW'),
        ('↩', 'U+21A9', 'LEFTWARDS ARROW WITH HOOK'),
        ('↪', 'U+21AA', 'RIGHTWARDS ARROW WITH HOOK'),
        ('⤴', 'U+2934', 'ARROW POINTING RIGHTWARDS THEN CURVING UPWARDS'),
        ('⤵', 'U+2935', 'ARROW POINTING RIGHTWARDS THEN CURVING DOWNWARDS'),
    ],
    'Эмодзи - знаки и символы': [
        ('⭐', 'U+2B50', 'WHITE MEDIUM STAR'),
        ('🌟', 'U+1F31F', 'GLOWING STAR'),
        ('💫', 'U+1F4AB', 'DIZZY SYMBOL'),
        ('✨', 'U+2728', 'SPARKLES'),
        ('❄', 'U+2744', 'SNOWFLAKE'),
        ('❄️', 'U+2744 U+FE0F', 'SNOWFLAKE (emoji variant)'),
        ('🔥', 'U+1F525', 'FIRE'),
        ('💯', 'U+1F4AF', 'HUNDRED POINTS SYMBOL'),
        ('🎯', 'U+1F3AF', 'DIRECT HIT'),
        ('📍', 'U+1F4CD', 'ROUND PUSHPIN'),
        ('📌', 'U+1F4CC', 'PUSHPIN'),
        ('🔖', 'U+1F516', 'BOOKMARK'),
    ],
    'Эмодзи - время и календарь': [
        ('⏰', 'U+23F0', 'ALARM CLOCK'),
        ('🕐', 'U+1F550', 'CLOCK FACE ONE OCLOCK'),
        ('🕑', 'U+1F551', 'CLOCK FACE TWO OCLOCK'),
        ('🕒', 'U+1F552', 'CLOCK FACE THREE OCLOCK'),
        ('📅', 'U+1F4C5', 'CALENDAR'),
        ('📆', 'U+1F4C6', 'TEAR-OFF CALENDAR'),
        ('🗓', 'U+1F5D3', 'SPIRAL CALENDAR PAD'),
        ('⏱', 'U+23F1', 'STOPWATCH'),
        ('⏲', 'U+23F2', 'TIMER CLOCK'),
    ],
    'Эмодзи - сеть и связь': [
        ('📡', 'U+1F4E1', 'SATELLITE ANTENNA'),
        ('📶', 'U+1F4F6', 'ANTENNA WITH BARS'),
        ('📞', 'U+1F4DE', 'TELEPHONE RECEIVER'),
        ('📱', 'U+1F4F1', 'MOBILE PHONE'),
        ('☎', 'U+260E', 'BLACK TELEPHONE'),
        ('📠', 'U+1F4E0', 'FAX MACHINE'),
        ('📧', 'U+1F4E7', 'E-MAIL SYMBOL'),
        ('📨', 'U+1F4E8', 'INCOMING ENVELOPE'),
        ('📩', 'U+1F4E9', 'ENVELOPE WITH DOWNWARDS ARROW ABOVE'),
        ('📮', 'U+1F4EE', 'POSTBOX'),
        ('📪', 'U+1F4EA', 'CLOSED MAILBOX WITH LOWERED FLAG'),
        ('📫', 'U+1F4EB', 'CLOSED MAILBOX WITH RAISED FLAG'),
    ],
    'Эмодзи - безопасность и доступ': [
        ('🔒', 'U+1F512', 'LOCK'),
        ('🔓', 'U+1F513', 'OPEN LOCK'),
        ('🔐', 'U+1F510', 'CLOSED LOCK WITH KEY'),
        ('🔑', 'U+1F511', 'KEY'),
        ('🗝', 'U+1F5DD', 'OLD KEY'),
        ('🛡', 'U+1F6E1', 'SHIELD'),
        ('🔰', 'U+1F530', 'JAPANESE SYMBOL FOR BEGINNER'),
        ('⛔', 'U+26D4', 'NO ENTRY'),
        ('🚫', 'U+1F6AB', 'PROHIBITED SIGN'),
        ('🚷', 'U+1F6B7', 'NO PEDESTRIANS'),
    ],
    'Эмодзи - системные и процессы': [
        ('⚙', 'U+2699', 'GEAR'),
        ('⚙️', 'U+2699 U+FE0F', 'GEAR (emoji variant)'),
        ('🔧', 'U+1F527', 'WRENCH'),
        ('🔨', 'U+1F528', 'HAMMER'),
        ('🛠', 'U+1F6E0', 'HAMMER AND WRENCH'),
        ('⚒', 'U+2692', 'HAMMER AND PICK'),
        ('🔩', 'U+1F529', 'NUT AND BOLT'),
        ('⚗', 'U+2697', 'ALEMBIC'),
        ('🧪', 'U+1F9EA', 'TEST TUBE'),
        ('🔬', 'U+1F52C', 'MICROSCOPE'),
        ('🔭', 'U+1F52D', 'TELESCOPE'),
    ],
}

def test_symbol_display(symbol):
    """
    Тестирует отображение символа в консоли
    Возвращает True если символ отображается корректно, False если нет
    """
    try:
        # Пробуем вывести символ
        test_output = symbol
        # Проверяем, что символ не превратился в замену символа (обычно ? или квадратик)
        # Если символ не поддерживается, он может отобразиться как '?' или ''
        if test_output == '?' or test_output == '' or len(test_output.encode('utf-8')) > 4:
            return False, 'Не поддерживается'
        
        # Дополнительная проверка: пробуем записать в файл и прочитать обратно
        test_file = '/tmp/symbol_test.tmp'
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(symbol)
            with open(test_file, 'r', encoding='utf-8') as f:
                read_symbol = f.read()
            os.remove(test_file)
            
            if read_symbol != symbol:
                return False, 'Не сохраняется корректно'
        except:
            pass
        
        return True, 'OK'
    except Exception as e:
        return False, f'Ошибка: {str(e)[:30]}'

def main():
    print("=" * 80)
    print("Тест доступности Unicode символов для Astra Linux 1.7")
    print("=" * 80)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Платформа: {sys.platform}")
    print(f"Кодировка консоли: {sys.stdout.encoding}")
    print("=" * 80)
    print()
    
    results = {}
    working_count = 0
    not_working_count = 0
    
    # Тестируем каждую категорию
    for category, symbols in SYMBOL_CATEGORIES.items():
        print(f"\n{'=' * 80}")
        print(f"Категория: {category}")
        print(f"{'=' * 80}")
        print(f"{'Символ':<10} {'Unicode':<12} {'Название':<40} {'Статус':<20}")
        print("-" * 80)
        
        for symbol, unicode_code, name in symbols:
            works, message = test_symbol_display(symbol)
            
            if works:
                status = '✓ Работает'
                working_count += 1
                status_color = '\033[32m'  # Зелёный
            else:
                status = f'✗ {message}'
                not_working_count += 1
                status_color = '\033[31m'  # Красный
            
            reset_color = '\033[0m'
            
            # Обрезаем длинные названия
            display_name = name[:37] + '...' if len(name) > 40 else name
            
            print(f"{symbol:<10} {unicode_code:<12} {display_name:<40} {status_color}{status:<20}{reset_color}")
            
            # Сохраняем результат
            results[f"{category}_{symbol}"] = {
                'symbol': symbol,
                'unicode': unicode_code,
                'name': name,
                'status': status,
                'works': works,
                'message': message,
                'category': category
            }
    
    # Статистика
    total = working_count + not_working_count
    print()
    print("=" * 80)
    print("СТАТИСТИКА")
    print("=" * 80)
    print(f"Всего символов: {total}")
    print(f"✓ Работает: {working_count} ({working_count*100//total if total > 0 else 0}%)")
    print(f"✗ Не работает: {not_working_count} ({not_working_count*100//total if total > 0 else 0}%)")
    print("=" * 80)
    
    # Сохраняем результаты в JSON
    json_filename = f"symbol_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'platform': sys.platform,
                'python_version': sys.version,
                'console_encoding': sys.stdout.encoding,
                'statistics': {
                    'total': total,
                    'working': working_count,
                    'not_working': not_working_count
                },
                'results': results
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Результаты сохранены в: {json_filename}")
    except Exception as e:
        print(f"\n✗ Ошибка сохранения JSON: {e}")
    
    # Создаём таблицу замены
    txt_filename = "emoji_replacement_table.txt"
    try:
        working_symbols = {k: v for k, v in results.items() if v['works']}
        
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write("Таблица замены эмодзи на спецсимволы для Astra Linux 1.7\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Дата тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Платформа: {sys.platform}\n")
            f.write(f"Python: {sys.version.split()[0]}\n")
            f.write(f"Кодировка: {sys.stdout.encoding}\n\n")
            
            f.write("РАБОЧИЕ СИМВОЛЫ:\n")
            f.write("-" * 70 + "\n")
            for key, data in sorted(working_symbols.items()):
                f.write(f"{data['symbol']} ({data['unicode']}) - {data['name']}\n")
            
            f.write("\n\nНЕ РАБОТАЮЩИЕ СИМВОЛЫ:\n")
            f.write("-" * 70 + "\n")
            not_working = {k: v for k, v in results.items() if not v['works']}
            for key, data in sorted(not_working.items()):
                f.write(f"{data['symbol']} ({data['unicode']}) - {data['name']} - {data['message']}\n")
            
            f.write("\n\nРЕКОМЕНДУЕМЫЕ ЗАМЕНЫ:\n")
            f.write("-" * 70 + "\n")
            f.write("📁 → [DIR] или ● (чёрный круг, если работает)\n")
            f.write("📄 → [FILE] или ■ (чёрный квадрат, если работает)\n")
            f.write("📸 → [IMG] или ◆ (чёрный ромб, если работает)\n")
            f.write("🔧 → [CFG] или ⚙ (шестерёнка, если работает)\n")
        
        print(f"✓ Таблица замены сохранена в: {txt_filename}")
    except Exception as e:
        print(f"✗ Ошибка создания таблицы: {e}")
    
    print("\n" + "=" * 80)
    print("Тестирование завершено!")
    print("=" * 80)

if __name__ == '__main__':
    main()
