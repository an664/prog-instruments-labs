#!/bin/bash

# Очистка временных файлов и кэша
find /app/data/raw -type f -mtime +7 -exec rm {} \;
find /app/logs -type f -mtime +30 -exec rm {} \;
find /app/data/processed -type f -mtime +30 -exec rm {} \;
