#!/bin/bash

# Instalar dependencias en el entorno del start
pip install -r requirements.txt --break-system-packages 2>/dev/null || \
pip install -r requirements.txt --user 2>/dev/null || \
pip install -r requirements.txt

# Ejecutar la app
python3 wsgi.py
