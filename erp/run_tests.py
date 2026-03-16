"""Script para rodar testes e capturar output no Windows."""
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_vendas.py", "tests/test_financeiro.py", "-v", "--tb=short"],
    cwd=r"C:\Users\Raphael\OneDrive\Área de Trabalho\claude raiz\erp",
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-2000:])
print("returncode:", result.returncode)
