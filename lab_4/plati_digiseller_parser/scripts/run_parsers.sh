#!/bin/bash

set -e  # Остановка скрипта при любой ошибке

# Полный цикл: парсинг -> запись в БД -> агрегация -> визуализация
python -m src.pipeline

# Очистка кэша
sh src/visualisation/clean_cache.sh

echo "Все операции выполнены успешно"
