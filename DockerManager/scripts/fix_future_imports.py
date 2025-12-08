#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт исправления __future__ импортов в объединенном файле
Версия: V3.3.166 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
from pathlib import Path

# Ищем файл из переменной окружения или используем по умолчанию
input_file = os.environ.get('INPUT_FILE', 'FSA-AstraInstall.py')
f = Path(input_file)
if not f.exists():
    f = Path(f'/build/{input_file}')

if f.exists():
    with open(f, 'r', encoding='utf-8') as file:
        lines = [l.rstrip('\n\r') for l in file.readlines()]
    
    future = [l.strip() for l in lines if l.strip().startswith('from __future__') or l.strip().startswith('import __future__')]
    other = [l for l in lines if not (l.strip().startswith('from __future__') or l.strip().startswith('import __future__'))]
    
    if future:
        enc_idx = next((i for i, l in enumerate(other) if 'coding' in l or 'encoding' in l), -1)
        if enc_idx >= 0:
            new = []
            for i, l in enumerate(other):
                new.append(l)
                if i == enc_idx:
                    new.extend(future)
            with open(f, 'w', encoding='utf-8') as file:
                file.write('\n'.join(new) + '\n')
            print(f'[OK] Исправлено: {len(future)} __future__ импортов', file=sys.stderr)
            sys.exit(0)
        else:
            print('[ERROR] Не найдена строка encoding!', file=sys.stderr)
            sys.exit(1)
    else:
        print('[INFO] __future__ импорты не найдены', file=sys.stderr)
        sys.exit(0)
else:
    print('[ERROR] Файл не найден!', file=sys.stderr)
    sys.exit(1)

