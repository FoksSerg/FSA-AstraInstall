# БЫСТРАЯ ИНСТРУКЦИЯ

## Обновление Python для GUI

1. Скопируйте папку FINAL_SOLUTION на Astra Linux машину
2. Запустите: `sudo bash install_python.sh`
3. Проверьте: `python3 --version`

## Запуск основной программы

После обновления Python:
```bash
sudo python astra-automation.py
```

## Если не работает

1. Запустите диагностику: `bash diagnose_python.sh`
2. Проверьте интернет соединение
3. Обратитесь к администратору

## Проверка Tkinter

```bash
python3 -c "import tkinter; print('OK')"
```

## Назначение

Этот пакет подготавливает Python для работы основной программы автоматизации, которая:
- Обновляет Astra Linux из репозиториев
- Устанавливает Wine и Astra.IDE
- Автоматически подтверждает все запросы