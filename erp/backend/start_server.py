"""
Launcher do backend ERP — injeta site-packages do Python 3.14 user-install
antes de subir o uvicorn, pois C:\Python314 é uma instalação mínima (sem pip/site).
"""
import sys, os

# Pacotes instalados pelo pip na instalação de usuário
USER_SITE = r"C:\Users\Raphael\AppData\Local\Programs\Python\Python314\Lib\site-packages"
if USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)

# Garante que o diretório do backend está no path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.chdir(BACKEND_DIR)

import uvicorn
uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
