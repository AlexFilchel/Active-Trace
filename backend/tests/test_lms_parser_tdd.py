"""TDD tests for lms_parser — detectar_actividades and extraer_calificaciones."""
from __future__ import annotations

import io

import openpyxl
import pytest

from app.services.lms_parser import detectar_actividades, extraer_calificaciones


def _make_xlsx(headers: list[str], rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# detectar_actividades
# ---------------------------------------------------------------------------


class TestDetectarActividades:
    def test_columnas_real_detectadas_como_numericas(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Tarea 1 (Real)", "Quiz (Real)", "Apellidos"],
            [["Ana", "85", "90", "García"]],
        )
        result = detectar_actividades(content, ".xlsx")
        assert result["actividades_numericas"] == ["Tarea 1 (Real)", "Quiz (Real)"]
        assert result["actividades_textuales"] == []

    def test_una_sola_columna_real(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Trabajo Final (Real)"],
            [["Ana", "70"]],
        )
        result = detectar_actividades(content, ".xlsx")
        assert result["actividades_numericas"] == ["Trabajo Final (Real)"]
        assert result["actividades_textuales"] == []

    def test_columnas_textuales_detectadas(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Trabajo Final", "Módulo 1"],
            [
                ["Ana", "Satisfactorio", "Supera lo esperado"],
                ["Luis", "No satisfactorio", "No alcanzado"],
            ],
        )
        result = detectar_actividades(content, ".xlsx")
        assert result["actividades_textuales"] == ["Trabajo Final", "Módulo 1"]
        assert result["actividades_numericas"] == []

    def test_columna_con_valor_textual_parcial_no_se_detecta(self) -> None:
        """Columna con mezcla de valores textuales y otros → no es textual."""
        content = _make_xlsx(
            ["Nombre", "Actividad X"],
            [
                ["Ana", "Satisfactorio"],
                ["Luis", "75"],  # valor numérico mezclado
            ],
        )
        result = detectar_actividades(content, ".xlsx")
        assert "Actividad X" not in result["actividades_textuales"]

    def test_columnas_mixtas_real_y_textual(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Tarea 1 (Real)", "Trabajo Final"],
            [["Ana", "85", "Satisfactorio"]],
        )
        result = detectar_actividades(content, ".xlsx")
        assert result["actividades_numericas"] == ["Tarea 1 (Real)"]
        assert result["actividades_textuales"] == ["Trabajo Final"]

    def test_sin_actividades_validas_retorna_listas_vacias(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Apellidos", "Email"],
            [["Ana", "García", "ana@test.com"]],
        )
        result = detectar_actividades(content, ".xlsx")
        assert result["actividades_numericas"] == []
        assert result["actividades_textuales"] == []

    def test_columnas_no_actividad_excluidas(self) -> None:
        """Columnas de identificación (Nombre, Email, etc.) no aparecen en resultados."""
        content = _make_xlsx(
            ["Nombre", "Apellidos", "Email", "Nota Global (Real)"],
            [["Ana", "García", "ana@test.com", "90"]],
        )
        result = detectar_actividades(content, ".xlsx")
        assert "Nombre" not in result["actividades_numericas"]
        assert "Apellidos" not in result["actividades_textuales"]
        assert "Nota Global (Real)" in result["actividades_numericas"]

    def test_csv_columnas_real_detectadas(self) -> None:
        csv_content = b"Nombre,Tarea 1 (Real),Quiz (Real)\nAna,85,90\nLuis,70,80\n"
        result = detectar_actividades(csv_content, ".csv")
        assert result["actividades_numericas"] == ["Tarea 1 (Real)", "Quiz (Real)"]

    def test_csv_sin_actividades(self) -> None:
        csv_content = b"Nombre,Apellidos\nAna,Garcia\n"
        result = detectar_actividades(csv_content, ".csv")
        assert result["actividades_numericas"] == []
        assert result["actividades_textuales"] == []


# ---------------------------------------------------------------------------
# extraer_calificaciones
# ---------------------------------------------------------------------------


class TestExtraerCalificaciones:
    def test_extrae_nota_numerica_por_actividad(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Apellidos", "Dirección de correo", "Tarea 1 (Real)", "Quiz (Real)"],
            [["Ana", "García", "ana@test.com", "85", "90"]],
        )
        rows = extraer_calificaciones(content, ".xlsx", ["Tarea 1 (Real)", "Quiz (Real)"])
        assert len(rows) == 2
        tarea = next(r for r in rows if r["actividad"] == "Tarea 1 (Real)")
        assert tarea["nota_numerica"] == pytest.approx(85.0)
        assert tarea["nota_textual"] is None
        assert tarea["email"] == "ana@test.com"

    def test_extrae_nota_textual_por_actividad(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Apellidos", "Dirección de correo", "Trabajo Final"],
            [["Ana", "García", "ana@test.com", "Satisfactorio"]],
        )
        rows = extraer_calificaciones(content, ".xlsx", ["Trabajo Final"])
        assert len(rows) == 1
        assert rows[0]["nota_textual"] == "Satisfactorio"
        assert rows[0]["nota_numerica"] is None

    def test_solo_incluye_actividades_seleccionadas(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Apellidos", "Dirección de correo", "Tarea 1 (Real)", "Quiz (Real)"],
            [["Ana", "García", "ana@test.com", "85", "90"]],
        )
        rows = extraer_calificaciones(content, ".xlsx", ["Tarea 1 (Real)"])
        actividades = [r["actividad"] for r in rows]
        assert "Quiz (Real)" not in actividades
        assert "Tarea 1 (Real)" in actividades

    def test_multiples_alumnos_multiples_actividades(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Apellidos", "Dirección de correo", "Tarea 1 (Real)"],
            [
                ["Ana", "García", "ana@test.com", "85"],
                ["Luis", "Pérez", "luis@test.com", "70"],
            ],
        )
        rows = extraer_calificaciones(content, ".xlsx", ["Tarea 1 (Real)"])
        assert len(rows) == 2
        emails = {r["email"] for r in rows}
        assert emails == {"ana@test.com", "luis@test.com"}

    def test_actividad_no_seleccionada_excluida(self) -> None:
        content = _make_xlsx(
            ["Nombre", "Apellidos", "Dirección de correo", "Tarea 1 (Real)", "Quiz (Real)"],
            [["Ana", "García", "ana@test.com", "85", "90"]],
        )
        rows = extraer_calificaciones(content, ".xlsx", [])
        assert rows == []

    def test_csv_extrae_correctamente(self) -> None:
        csv_content = b"Nombre,Apellidos,Direcci\xc3\xb3n de correo,Tarea 1 (Real)\nAna,Garc\xc3\xada,ana@test.com,85\n"
        rows = extraer_calificaciones(csv_content, ".csv", ["Tarea 1 (Real)"])
        assert len(rows) == 1
        assert rows[0]["nota_numerica"] == pytest.approx(85.0)
