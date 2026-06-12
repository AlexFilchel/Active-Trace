from __future__ import annotations

import csv
import io
import unicodedata


REQUIRED_COLUMNS = {"nombre", "apellidos", "email"}
COLUMN_ALIASES: dict[str, str] = {
    "nombre": "nombre",
    "apellido": "apellidos",
    "apellidos": "apellidos",
    "apellido(s)": "apellidos",
    "dirección de correo": "email",
    "direccion de correo": "email",
    "direccion de correo electronico": "email",
    "email": "email",
    "correo": "email",
    "correo electrónico": "email",
    "correo electronico": "email",
    "grupos": "comision",
    "grupo": "comision",
    "comisión": "comision",
    "comision": "comision",
    "regional": "regional",
    "sede": "regional",
}


class ParseError(Exception):
    def __init__(self, detail: str, missing_columns: list[str] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.missing_columns = missing_columns or []


def _normalize(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _map_headers(raw_headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in raw_headers:
        normalized = _normalize(raw)
        canonical = COLUMN_ALIASES.get(normalized)
        if canonical and canonical not in mapping:
            mapping[canonical] = raw
    return mapping


def parse_file(content: bytes, filename: str) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        return _parse_xlsx(content)
    if lower.endswith(".csv"):
        return _parse_csv(content)
    raise ParseError(f"Formato de archivo no soportado: {filename}. Use .xlsx o .csv")


def _validate_and_map(raw_headers: list[str]) -> dict[str, str]:
    mapping = _map_headers(raw_headers)
    missing = [col for col in REQUIRED_COLUMNS if col not in mapping]
    if missing:
        raise ParseError(
            f"Columnas obligatorias faltantes: {', '.join(missing)}",
            missing_columns=missing,
        )
    return mapping


def _row_to_dict(row: dict[str, str], col_map: dict[str, str]) -> dict:
    return {
        "nombre": row.get(col_map["nombre"], "").strip(),
        "apellidos": row.get(col_map["apellidos"], "").strip(),
        "email": row.get(col_map["email"], "").strip(),
        "comision": row.get(col_map.get("comision", ""), "").strip() if "comision" in col_map else None,
        "regional": row.get(col_map.get("regional", ""), "").strip() if "regional" in col_map else None,
    }


def _parse_xlsx(content: bytes) -> list[dict]:
    try:
        import openpyxl
    except ImportError as exc:
        raise ParseError("openpyxl no está instalado. Instale con: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ParseError("El archivo no contiene alumnos")

    raw_headers = [str(h) if h is not None else "" for h in rows[0]]
    col_map = _validate_and_map(raw_headers)

    header_index = {raw: i for i, raw in enumerate(raw_headers)}

    result = []
    for row in rows[1:]:
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        row_dict = {h: (str(row[i]) if row[i] is not None else "") for h, i in header_index.items()}
        result.append(_row_to_dict(row_dict, col_map))

    if not result:
        raise ParseError("El archivo no contiene alumnos")

    return result


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ParseError("El archivo no contiene alumnos")

    col_map = _validate_and_map(list(reader.fieldnames))

    result = []
    for row in reader:
        if all(not v.strip() for v in row.values()):
            continue
        result.append(_row_to_dict(dict(row), col_map))

    if not result:
        raise ParseError("El archivo no contiene alumnos")

    return result
