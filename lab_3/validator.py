import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Pattern

from checksum import calculate_checksum, serialize_result

CSV_DELIMITER = ";"
CSV_ENCODING = "utf-16"
VARIANT = 11
CSV_FILENAME = f"{VARIANT}.csv"

PATTERN_DEFINITIONS: Dict[str, str] = {
    "email": (
        r"^[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*@"
        r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+$"
    ),
    "height": r"^(?:0\.[0-9]{2}|1\.[0-9]{2}|2\.[0-9]{2})$",
    "snils": r"^\d{11}$",
    "passport": r"^\d{2}\s\d{2}\s\d{6}$",
    "occupation": r"^[A-Za-zА-Яа-яЁё]+(?:[ -][A-Za-zА-Яа-яЁё]+)*$",
    "longitude": r"^[-+]?(?:180(?:\.0+)?|(?:1[0-7]\d|\d?\d)(?:\.\d+)?)$",
    "hex_color": r"^#[0-9a-fA-F]{6}$",
    "issn": r"^\d{4}-\d{4}$",
    "locale_code": r"^[a-z]{2}(?:-[a-z]{2})?$",
    "time": r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\.\d{6}$",
}


def compile_patterns() -> Dict[str, Pattern[str]]:
    return {field: re.compile(pattern) for field, pattern in PATTERN_DEFINITIONS.items()}


def read_rows(csv_path: Path) -> Iterable[dict]:
    with csv_path.open(encoding=CSV_ENCODING, newline="") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=CSV_DELIMITER)
        yield from reader


def find_invalid_rows(rows: Iterable[dict], patterns: Dict[str, Pattern[str]]) -> List[int]:
    invalid_rows: List[int] = []
    for index, row in enumerate(rows):
        for field, pattern in patterns.items():
            if not pattern.fullmatch(row[field]):
                invalid_rows.append(index)
                break
    return invalid_rows


def main() -> None:
    base_dir = Path(__file__).parent
    csv_path = base_dir / CSV_FILENAME
    patterns = compile_patterns()
    rows = list(read_rows(csv_path))
    invalid_rows = find_invalid_rows(rows, patterns)
    checksum = calculate_checksum(invalid_rows)
    serialize_result(variant=VARIANT, checksum=checksum)
    print(f"Found {len(invalid_rows)} invalid rows. Checksum: {checksum}")


if __name__ == "__main__":
    main()
