#!/bin/bash

set -e  # Остановка скрипта при любой ошибке

# Обработка и визуализация данных
python -m src.data_processing.data_processor
python -m src.visualisation.data_visualisation

# Очистка кэша
sh src/visualisation/clean_cache.sh

echo "Все операции выполнены успешно"
