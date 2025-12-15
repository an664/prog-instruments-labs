#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Очистка временных файлов и кэша
find "$ROOT_DIR/data/raw" -type f -mtime +7 -exec rm {} \; 2>/dev/null || true
find "$ROOT_DIR/logs" -type f -mtime +30 -exec rm {} \; 2>/dev/null || true
find "$ROOT_DIR/data/processed" -type f -mtime +30 -exec rm {} \; 2>/dev/null || true
