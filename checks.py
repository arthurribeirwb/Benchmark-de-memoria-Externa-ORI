"""
Verificações de ambiente antes de rodar qualquer coisa.

Confere se o executável 'fio' e o comando 'fio-plot' (instalado pelo
pacote fio-plot via pip) estão disponíveis, e resolve o caminho
completo de cada um — usado tanto pela checagem quanto pelas chamadas
reais de subprocess em benchmark_core.py (ver find_executable).
"""

import os
import shutil
import sys


def find_executable(name: str):
    """
    Procura um executável, primeiro no PATH do sistema e, se não achar,
    na mesma pasta do interpretador Python que está rodando agora
    (Scripts\\ no Windows, bin/ no Linux, dentro do venv).

    O segundo caso é necessário porque os scripts setup_and_run.bat/.sh
    chamam o Python de dentro do venv diretamente (ex:
    "venv\\Scripts\\python.exe gui.py"), sem "ativar" o venv — e sem
    ativação, a pasta Scripts/bin do venv não entra no PATH do
    processo, mesmo com os pacotes instalados corretamente lá dentro.
    Sem essa segunda busca, o programa (e o subprocess que chama o
    fio-plot de verdade) não encontraria o comando.

    Retorna o caminho completo se encontrar, ou None.
    """
    path = shutil.which(name)
    if path:
        return path

    venv_bin_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates = [f"{name}.exe", name] if os.name == "nt" else [name]
    for candidate in candidates:
        candidate_path = os.path.join(venv_bin_dir, candidate)
        if os.path.isfile(candidate_path):
            return candidate_path
    return None


def check_executable(name: str):
    """Retorna (ok: bool, caminho_ou_dica: str)."""
    path = find_executable(name)
    if path is None:
        return False, None
    return True, path


INSTALL_HINTS = {
    "fio": (
        "FIO não encontrado. Windows: baixe o instalador oficial "
        "(fio-X.XX-x64.msi) em https://github.com/axboe/fio/releases. "
        "Linux: 'sudo apt install fio'."
    ),
    "fio-plot": (
        "fio-plot não encontrado. Rode 'pip install -r requirements.txt' "
        "dentro do seu ambiente virtual."
    ),
}


def run_all_checks() -> list:
    """
    Retorna uma lista de tuplas (nome, ok, caminho_ou_dica) para cada
    dependência checada. Não imprime nada — quem chama decide como
    mostrar (terminal ou GUI).
    """
    results = []
    for name in ("fio", "fio-plot"):
        ok, path = check_executable(name)
        info = path if ok else INSTALL_HINTS[name]
        results.append((name, ok, info))
    return results


if __name__ == "__main__":
    for name, ok, info in run_all_checks():
        status = "OK" if ok else "FALTANDO"
        print(f"[{status}] {name}: {info}")
