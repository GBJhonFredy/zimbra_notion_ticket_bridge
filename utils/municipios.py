# utils/municipios.py
from __future__ import annotations

from typing import Optional, Set
import os

import pandas as pd  # type: ignore

from config.settings import settings

MUNICIPIO_COLUMN = "Municipio"  # cambia si la columna tiene otro nombre

# Cache en memoria
_MUNICIPIOS_NORMALIZADOS: Set[str] | None = None


def _cargar_municipios_desde_excel() -> Set[str]:
    excel_path = settings.municipios.excel_path
    if not excel_path or not os.path.exists(excel_path):
        return set()

    # Lee todas las hojas en un dict de DataFrames
    sheets = pd.read_excel(excel_path, sheet_name=None)

    nombres: Set[str] = set()
    for df in sheets.values():
        if MUNICIPIO_COLUMN not in df.columns:
            continue
        # Tomamos los valores no nulos de esa columna
        for raw in df[MUNICIPIO_COLUMN].dropna().astype(str):
            raw = raw.strip()
            if not raw:
                continue
            nombres.add(raw)

    return nombres


def _ensure_cache() -> Set[str]:
    global _MUNICIPIOS_NORMALIZADOS
    if _MUNICIPIOS_NORMALIZADOS is None:
        originales = _cargar_municipios_desde_excel()
        # normalizamos a minúsculas para comparar por substring
        _MUNICIPIOS_NORMALIZADOS = {m.lower() for m in originales}
    return _MUNICIPIOS_NORMALIZADOS


def _formatear_municipio(nombre: str) -> str:
    """
    Convierte 'jamundí', 'JAMUNDI', 'JaMuNdí' -> 'Jamundí'
    (primera letra mayúscula, resto minúsculas, respetando acentos).
    """
    if not nombre:
        return nombre
    nombre = nombre.strip()
    if not nombre:
        return nombre
    return nombre[0].upper() + nombre[1:].lower()


def detect_municipio(texto: str) -> Optional[str]:
    """
    Busca cualquier municipio del Excel mencionado en el texto (substring,
    sin distinguir mayúsculas/minúsculas). Devuelve el nombre formateado.
    """
    if not texto:
        return None

    municipios = _ensure_cache()
    lower_text = texto.lower()

    # Buscamos el primer municipio cuyo nombre aparezca como substring
    for nombre_lower in municipios:
        if nombre_lower in lower_text:
            return _formatear_municipio(nombre_lower)

    return None
