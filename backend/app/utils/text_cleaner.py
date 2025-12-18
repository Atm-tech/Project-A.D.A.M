import re


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_name(text: str) -> str:
    """
    Clean article / product name:
    - strip, collapse spaces
    - uppercase
    """
    text = normalize_whitespace(text)
    return text.upper()


def normalize_barcode(text: str) -> str:
    """
    Barcodes as string, no spaces.
    """
    if text is None:
        return ""
    text = str(text).strip()
    text = text.replace(" ", "")
    return text
