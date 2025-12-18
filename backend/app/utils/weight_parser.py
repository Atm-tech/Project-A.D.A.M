import re
from typing import Optional, Tuple

# Example matches:
#  "FORTUNE OIL 1 LTR"
#  "RICE 5KG"
#  "MILK 500 ML"
WEIGHT_REGEX = re.compile(
    r"(\d+(?:\.\d+)?)\s*(KG|KGS?|G|GM|GMS|GRAMS?|L|LTRS?|ML|PCS?|PC|PKT|PACK)",
    re.IGNORECASE,
)

UNIT_MAP = {
    "KGS": "KG",
    "KG": "KG",
    "G": "GM",
    "GM": "GM",
    "GMS": "GM",
    "GRAM": "GM",
    "GRAMS": "GM",
    "L": "LTR",
    "LTR": "LTR",
    "LTRS": "LTR",
    "ML": "ML",
    "PC": "PCS",
    "PCS": "PCS",
    "PACK": "PKT",
    "PKT": "PKT",
}


def parse_weight(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts a (value, unit) from article_name.

    Returns (None, None) if nothing found.
    """
    if not text:
        return None, None

    match = WEIGHT_REGEX.search(str(text))
    if not match:
        return None, None

    value_str = match.group(1)
    unit_raw = match.group(2).upper()

    try:
        value = float(value_str)
    except ValueError:
        return None, None

    unit = UNIT_MAP.get(unit_raw, unit_raw)
    return value, unit
