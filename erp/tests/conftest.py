import sys
import os

# Garante que o backend está no sys.path para os testes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
