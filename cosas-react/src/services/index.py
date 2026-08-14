"""Punto de entrada de FastAPI para Vercel.

Vercel ejecuta las funciones Python dentro de la carpeta ``api``. La
aplicación real continúa en ``main.py`` para que también funcione sin cambios
en Codespaces y en desarrollo local.
"""
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app

