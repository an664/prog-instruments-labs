#!/bin/bash

set -e  # Остановка скрипта при любой ошибке

# Запуск парсеров
python src/parsers/plati_market_parser.py
python src/parsers/digiseller_api.py

# Обработка и визуализация данных
python src/data_processing/data_processor.py
python src/visualisation/data_visualisation.py

# Очистка кэша
sh scripts/clean_cache.sh

echo "Все операции выполнены успешно"
