from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any


def _to_utf16_code_units(text: str) -> list[int]:
    raw = text.encode("utf-16-le")
    return [raw[i] | (raw[i + 1] << 8) for i in range(0, len(raw), 2)]


def _from_utf16_code_units(units: list[int]) -> str:
    raw = bytearray()
    for unit in units:
        raw.append(unit & 0xFF)
        raw.append((unit >> 8) & 0xFF)
    return raw.decode("utf-16-le")


def xor_js_string(text: str, key: str) -> str:
    if not key:
        raise ValueError("Encryption key cannot be empty")
    text_units = _to_utf16_code_units(text)
    key_units = _to_utf16_code_units(key)
    out_units = [unit ^ key_units[i % len(key_units)] for i, unit in enumerate(text_units)]
    return _from_utf16_code_units(out_units)


def encode_payload(data: Any, key: str) -> str:
    xored = xor_js_string(json.dumps(data, ensure_ascii=False, separators=(",", ":")), key)
    return base64.b64encode(xored.encode("utf-8")).decode("ascii")


def decode_payload(encoded: str, key: str) -> Any:
    decoded = base64.b64decode(encoded).decode("utf-8")
    return json.loads(xor_js_string(decoded, key))


def read_encrypted_json(path: str | Path, key: str) -> Any:
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    return decode_payload(raw, key)


def write_encrypted_json(path: str | Path, data: Any, key: str) -> None:
    Path(path).write_text(encode_payload(data, key), encoding="utf-8")
