# utils/municipios.py
from __future__ import annotations

from typing import Optional, Set
import os

import pandas as pd  # type: ignore

from config.settings import settings

MUNICIPIO_COLUMN = "Municipio"  # cambia si la columna tiene otro nombre

# Cache en memoria para no releer el Excel en cada correo procesado.
_MUNICIPIOS_NORMALIZADOS: Set[str] | None = None


def _cargar_municipios_desde_excel() -> Set[str]:
    # Toma la ruta desde settings cargados desde .env.
    excel_path = settings.municipios.excel_path
    # Si no hay ruta o el archivo no existe, retorna set vacio.
    if not excel_path or not os.path.exists(excel_path):
        return set()

    # Lee todas las hojas en un dict de DataFrames: {nombre_hoja: dataframe}.
    sheets = pd.read_excel(excel_path, sheet_name=None)

    nombres: Set[str] = set()
    # Recorre cada hoja buscando la columna esperada.
    for df in sheets.values():
        if MUNICIPIO_COLUMN not in df.columns:
            continue
        # Tomamos los valores no nulos de esa columna
        # dropna() limpia vacios; astype(str) permite normalizar entradas mixtas.
        for raw in df[MUNICIPIO_COLUMN].dropna().astype(str):
            raw = raw.strip()
            if not raw:
                continue
            # Set evita duplicados automaticamente.
            nombres.add(raw)

    return nombres


def _ensure_cache() -> Set[str]:
    global _MUNICIPIOS_NORMALIZADOS
    if _MUNICIPIOS_NORMALIZADOS is None:
        originales = _cargar_municipios_desde_excel()
        # normalizamos a minúsculas para comparar por substring
        _MUNICIPIOS_NORMALIZADOS = {m.lower() for m in originales}
    # Devuelve cache ya listo (inicializado una sola vez por proceso).
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
    # Formato canonico simple: primera letra mayuscula y resto minuscula.
    return nombre[0].upper() + nombre[1:].lower()


def detect_municipio(texto: str) -> Optional[str]:
    """
    Busca cualquier municipio del Excel mencionado en el texto (substring,
    sin distinguir mayúsculas/minúsculas). Devuelve el nombre formateado.
    """
    if not texto:
        return None

    # Trae cache precargado de municipios normalizados.
    municipios = _ensure_cache()
    # Normaliza texto de correo para comparar sin sensibilidad a mayusculas.
    lower_text = texto.lower()

    # Buscamos el primer municipio cuyo nombre aparezca como substring
    # Recorre set de municipios y retorna en cuanto encuentra coincidencia.
    for nombre_lower in municipios:
        if nombre_lower in lower_text:
            return _formatear_municipio(nombre_lower)

    # Si no hay match, caller enviara municipio=None a Notion.
    return None
