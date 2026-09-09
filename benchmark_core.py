"""
Lógica central do exercício: rodar o FIO e gerar os 3 gráficos com o
fio-plot. Este módulo não sabe nada sobre interface — tanto a GUI
(gui.py) quanto um uso futuro por linha de comando podem chamar as
funções daqui, passando um `log_callback(str)` para receber mensagens
de progresso linha a linha.

=== Por que não usar o 'bench-fio' ===

O 'bench-fio' (ferramenta que acompanha o pacote fio-plot) tenta
"limpar" o cache do sistema antes de cada rodada, rodando, sem checar o
SO, o comando `echo 3 > /proc/sys/vm/drop_caches` — que só existe no
Linux. No Windows isso quebra com `FileNotFoundError: [WinError 2]`, e
não tem flag pra desativar (está fixo no código do bench-fio). Por
isso chamamos o `fio` diretamente e montamos nós mesmos os arquivos no
formato que o fio-plot espera — funciona igual nos dois sistemas.

=== Sobre o tamanho do teste ===

A primeira versão deste projeto usava um arquivo de 256 MB por 5
segundos por iodepth — pequeno e rápido demais: com --direct=1 o
arquivo inteiro cabe facilmente na janela de acesso que o FIO passa
revisitando repetidamente, e o padrão de acesso aleatório fica
concentrado numa área pequena do "disco" (arquivo), o que infla os
IOPS e esconde variações reais de latência. Usamos por padrão um
arquivo maior (1 GiB) e um pouco mais de tempo por rodada (8 s), o que
dá ao acesso aleatório uma faixa de endereços bem maior pra "espalhar"
— mais parecido com o que aconteceria testando um SSD/HD de verdade —
mantendo o teste todo em menos de 1 minuto, viável pra rodar ao vivo
num seminário. Ambos os valores são ajustáveis na GUI.

=== SEGURANÇA ===

O alvo do teste é SEMPRE um arquivo comum dentro da pasta `data/`
deste projeto (TARGET_FILE), nunca um disco físico
(/dev/sdX, \\\\.\\PhysicalDriveN etc.).
"""

import pathlib
import platform
import shutil
import subprocess
import json

import checks

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
TARGET_FILE = DATA_DIR / "testfile.bin"
RESULTS_DIR = DATA_DIR / "results"
OUTPUT_DIR = PROJECT_ROOT / "output"

# --- Valores padrão (editáveis na GUI) ---
DEFAULT_SIZE_MB = 1024        # 1 GiB — grande o bastante pra não ficar todo "quente" em cache
DEFAULT_RUNTIME_S = 8         # segundos por combinação de iodepth
DEFAULT_IODEPTHS = [1, 4, 8, 16]
NUMJOBS = 1
MODE = "randread"             # leitura aleatória — não altera/apaga dados
BLOCK_SIZE = "4k"


def pick_ioengine() -> str:
    """
    Escolhe o ioengine de acordo com o SO, porque --direct=1 (bypassar o
    cache do sistema operacional, essencial pra medir o disco de
    verdade) não é suportado da mesma forma nos dois sistemas:

    - No Windows, o ioengine 'sync' NÃO suporta --direct=1 (o próprio
      FIO recusa rodar e sugere 'windowsaio' — foi exatamente o erro
      que apareceu). Então usamos 'windowsaio' no Windows.
    - No Linux, 'sync' com --direct=1 funciona normalmente. 'libaio' é
      o ioengine mais usado em benchmarks reais de storage no Linux,
      mas exige que o FIO tenha sido compilado com suporte a ele — nem
      todo pacote garante isso, então mantemos 'sync' como padrão
      seguro (pode trocar para 'libaio' aqui se quiser testar).
    """
    if platform.system() == "Windows":
        return "windowsaio"
    return "sync"


def check_fio_available() -> bool:
    return checks.find_executable("fio") is not None


def ensure_target_file(size_mb: int, log=print) -> None:
    """Garante que o arquivo de teste existe, com o tamanho pedido."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    size_bytes = size_mb * 1024 * 1024
    if TARGET_FILE.exists() and TARGET_FILE.stat().st_size == size_bytes:
        log(f"Arquivo de teste já existe com o tamanho certo ({size_mb} MiB).")
        return
    log(f"Criando arquivo de teste: {TARGET_FILE} ({size_mb} MiB)")
    with open(TARGET_FILE, "wb") as f:
        f.truncate(size_bytes)


def _stream_subprocess(cmd: list, log) -> int:
    """Roda um comando e envia cada linha de saída para o log em tempo real."""
    process = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in process.stdout:
        log(line.rstrip())
    process.wait()
    return process.returncode


def run_one_fio_job(iodepth: int, size_mb: int, runtime_s: int, log=print) -> None:
    """
    Roda o FIO para UMA combinação de iodepth.

    O resultado JSON é capturado direto da saída padrão do processo (em
    memória) e só depois escrito em disco por nós mesmos — em vez de
    deixar o FIO escrever sozinho via --output. Isso evita uma
    inconsistência observada no Windows: o FIO retorna código 0 (sucesso)
    mas o arquivo passado em --output às vezes fica vazio, porque o
    conteúdo ainda não tinha sido sincronizado no disco quando o
    processo "terminou" do ponto de vista do Python. Capturando via
    stdout, sabemos com certeza que o conteúdo já está todo em memória
    antes de gravar o arquivo.
    """
    engine = pick_ioengine()
    name = f"{MODE}-iodepth-{iodepth}-numjobs-{NUMJOBS}"
    json_path = RESULTS_DIR / f"{name}.json"
    log_base = RESULTS_DIR / name

    cmd = [
        checks.find_executable("fio") or "fio",
        f"--name={name}",
        f"--filename={TARGET_FILE}",
        f"--rw={MODE}",
        f"--bs={BLOCK_SIZE}",
        f"--ioengine={engine}",
        f"--iodepth={iodepth}",
        f"--numjobs={NUMJOBS}",
        "--direct=1",
        f"--size={size_mb}M",
        f"--runtime={runtime_s}",
        "--time_based",
        "--group_reporting",
        "--output-format=json",
        # sem --output=...: o JSON sai pela stdout, que nós capturamos
        f"--write_iops_log={log_base}",
        f"--write_lat_log={log_base}",
        "--log_avg_msec=1000",
    ]
    log(f"\n>> Rodando FIO (iodepth={iodepth}, runtime={runtime_s}s)...")

    process = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_data, stderr_data = process.communicate()

    for line in stderr_data.splitlines():
        if line.strip():
            log(line.rstrip())

    if process.returncode != 0:
        raise RuntimeError(f"fio terminou com código {process.returncode} (iodepth={iodepth})")

    stdout_data = stdout_data.strip()
    if not stdout_data:
        raise RuntimeError(
            f"O fio não produziu nenhuma saída JSON (iodepth={iodepth}), mesmo "
            f"tendo terminado com sucesso. Tente rodar de novo; se persistir, "
            f"pode ser antivírus interferindo na execução do fio.exe."
        )

    # O fio às vezes imprime avisos de texto (ex: "note: ... queue depth
    # will be capped at 1", comum quando iodepth > 1 com ioengine=sync)
    # ANTES do JSON, na mesma saída padrão. Pegamos só a partir do
    # primeiro '{' pra ignorar qualquer aviso desse tipo.
    json_start = stdout_data.find("{")
    if json_start == -1:
        raise RuntimeError(
            f"A saída do fio não contém nenhum JSON (iodepth={iodepth}). "
            f"Saída recebida: {stdout_data[:300]!r}"
        )
    stdout_data = stdout_data[json_start:]

    try:
        json.loads(stdout_data)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"A saída do fio não é um JSON válido (iodepth={iodepth}): {exc}"
        ) from exc

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(stdout_data, encoding="utf-8")


def run_benchmark(
    size_mb: int = DEFAULT_SIZE_MB,
    runtime_s: int = DEFAULT_RUNTIME_S,
    iodepths: list = None,
    log=print,
) -> pathlib.Path:
    """Roda o benchmark completo (todas as combinações de iodepth). Retorna a pasta de resultados."""
    iodepths = iodepths or DEFAULT_IODEPTHS

    if not check_fio_available():
        raise RuntimeError("'fio' não encontrado no PATH. Instale o FIO antes de continuar.")

    ensure_target_file(size_mb, log=log)

    if RESULTS_DIR.exists():
        shutil.rmtree(RESULTS_DIR)
    RESULTS_DIR.mkdir(parents=True)

    log(f"Sistema operacional detectado: {platform.system()}")
    for iodepth in iodepths:
        run_one_fio_job(iodepth, size_mb, runtime_s, log=log)

    log(f"\nDados do benchmark salvos em: {RESULTS_DIR}")
    return RESULTS_DIR


def generate_plots(data_dir: pathlib.Path, iodepths: list = None, log=print) -> dict:
    """Gera os 3 gráficos com fio-plot. Retorna um dict {nome: caminho_png}."""
    iodepths = iodepths or DEFAULT_IODEPTHS
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {}

    charts = [
        (
            "3d_bar_chart",
            [
                "-T", "IOPS por fila de requisicao (3D) - randread",
                "-L", "-r", "randread", "-t", "iops",
            ],
        ),
        (
            "line_chart",
            [
                "-T", "IOPS ao longo do tempo - randread",
                "-g", "-r", "randread", "-t", "iops",
                "-d", *[str(d) for d in iodepths], "-n", "1",
            ],
        ),
        (
            "latency_histogram",
            [
                "-T", "Histograma de latencia - randread (qd=1)",
                "-H", "-r", "randread", "-d", "1", "-n", "1",
            ],
        ),
    ]

    for filename, extra_args in charts:
        out_path = OUTPUT_DIR / f"{filename}.png"
        cmd = [checks.find_executable("fio-plot") or "fio-plot", "-i", str(data_dir), *extra_args, "-o", str(out_path)]
        log(f"\n>> Gerando {filename}...")
        returncode = _stream_subprocess(cmd, log)
        if returncode != 0:
            raise RuntimeError(f"fio-plot falhou gerando {filename} (código {returncode})")
        outputs[filename] = out_path

    return outputs
