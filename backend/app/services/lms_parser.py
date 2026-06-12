"""Parser de archivos exportados desde el LMS (Moodle gradebook).

Detecta actividades numéricas (columnas que terminan en "(Real)", RN-01)
y textuales (columnas cuyo conjunto de valores ⊆ VALORES_TEXTUALES, RN-02).
No persiste nada — todas las funciones son stateless.
"""
from __future__ import annotations

import csv
import io
import unicodedata
from typing import Any

VALORES_TEXTUALES = {"Satisfactorio", "Supera lo esperado", "No satisfactorio", "No alcanzado"}

_COLUMNAS_IDENTIDAD = {
    "nombre",
    "apellidos",
    "apellido",
    "email",
    "correo",
    "dirección de correo",
    "direccion de correo",
    "dirección de correo electrónico",
    "id",
    "legajo",
    "comisión",
    "comision",
    "grupo",
    "grupos",
    "regional",
    "sede",
    "estado",
    "número de identificación",
    "numero de identificacion",
}


def _normalize(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _is_identity_column(header: str) -> bool:
    return _normalize(header) in _COLUMNAS_IDENTIDAD


def _is_numeric_column(header: str) -> bool:
    return header.strip().endswith("(Real)")


def _is_textual_column(header: str, column_values: list[str]) -> bool:
    non_empty = [v for v in column_values if v.strip()]
    if not non_empty:
        return False
    return all(v.strip() in VALORES_TEXTUALES for v in non_empty)


def _load_rows_xlsx(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    raw = list(ws.iter_rows(values_only=True))
    if not raw:
        return [], []
    headers = [str(h) if h is not None else "" for h in raw[0]]
    rows = []
    for row in raw[1:]:
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        rows.append({headers[i]: (str(row[i]) if row[i] is not None else "") for i in range(len(headers))})
    return headers, rows


def _load_rows_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader if any(v.strip() for v in row.values())]
    return headers, rows


def _load_rows(content: bytes, extension: str) -> tuple[list[str], list[dict[str, str]]]:
    ext = extension.lower()
    if ext == ".xlsx":
        return _load_rows_xlsx(content)
    if ext == ".csv":
        return _load_rows_csv(content)
    raise ValueError(f"Formato no soportado: {extension}")


def _find_email_column(headers: list[str]) -> str | None:
    email_keys = {"email", "correo", "dirección de correo", "direccion de correo", "dirección de correo electrónico", "correo electrónico", "correo electronico"}
    for h in headers:
        if _normalize(h) in email_keys:
            return h
    return None


def detectar_actividades(content: bytes, extension: str) -> dict[str, list[str]]:
    """Analiza el archivo LMS en memoria y clasifica las columnas de actividad.

    Returns:
        {"actividades_numericas": [...], "actividades_textuales": [...]}
    """
    headers, rows = _load_rows(content, extension)

    actividades_numericas: list[str] = []
    actividades_textuales: list[str] = []

    for header in headers:
        if not header.strip() or _is_identity_column(header):
            continue
        if _is_numeric_column(header):
            actividades_numericas.append(header)
        else:
            column_values = [row.get(header, "") for row in rows]
            if _is_textual_column(header, column_values):
                actividades_textuales.append(header)

    return {"actividades_numericas": actividades_numericas, "actividades_textuales": actividades_textuales}


def extraer_calificaciones(
    content: bytes,
    extension: str,
    actividades_seleccionadas: list[str],
) -> list[dict[str, Any]]:
    """Extrae filas de calificación para las actividades seleccionadas.

    Returns una lista de dicts con keys:
        email, actividad, nota_numerica (float | None), nota_textual (str | None)
    """
    if not actividades_seleccionadas:
        return []

    headers, rows = _load_rows(content, extension)
    email_col = _find_email_column(headers)
    seleccionadas_set = set(actividades_seleccionadas)

    resultado: list[dict[str, Any]] = []
    for row in rows:
        email = row.get(email_col, "").strip() if email_col else ""
        for actividad in actividades_seleccionadas:
            if actividad not in seleccionadas_set:
                continue
            raw_val = row.get(actividad, "").strip()
            nota_numerica: float | None = None
            nota_textual: str | None = None

            if actividad.endswith("(Real)"):
                try:
                    nota_numerica = float(raw_val)
                except (ValueError, TypeError):
                    nota_numerica = None
            elif raw_val in VALORES_TEXTUALES:
                nota_textual = raw_val
            elif raw_val:
                nota_textual = raw_val

            resultado.append({
                "email": email,
                "actividad": actividad,
                "nota_numerica": nota_numerica,
                "nota_textual": nota_textual,
            })

    return resultado
