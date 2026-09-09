# FIO Bench GUI

Interface gráfica em Python (Tkinter/ttk) para rodar benchmarks reais de
armazenamento com o [FIO](https://github.com/axboe/fio) e visualizar os
resultados com o [fio-plot](https://github.com/louwrentius/fio-plot) —
sem precisar tocar em terminal além de abrir o programa.

Projeto desenvolvido para o Exercício 1 da disciplina de Organização e
Recuperação da Informação (ORI).

## Sumário

- [Visão geral](#visão-geral)
- [Gráficos gerados](#gráficos-gerados)
- [Requisitos](#requisitos)
- [Instalação e execução](#instalação-e-execução)
- [Como usar](#como-usar)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Metodologia do benchmark](#metodologia-do-benchmark)
- [Decisões técnicas](#decisões-técnicas)
- [Segurança](#segurança)

## Visão geral

O programa roda um benchmark de leitura aleatória (`randread`) contra um
arquivo local, usando o FIO diretamente, e gera três visualizações com o
`fio-plot`:

- **3D Bar Chart** — IOPS por fila de requisição (iodepth)
- **Line Chart** — IOPS ao longo do tempo, por iodepth
- **Latency Histogram** — distribuição de latência das operações

Tudo acontece dentro de uma única janela: configuração dos parâmetros,
execução do benchmark com log em tempo real, e exibição dos gráficos em
abas, assim que ficam prontos.

## Gráficos gerados

| 3D Bar Chart | Line Chart | Latency Histogram |
|---|---|---|
| ![3D Bar Chart](output/3d_bar_chart.png) | ![Line Chart](output/line_chart.png) | ![Latency Histogram](output/latency_histogram.png) |

## Requisitos

- Python 3.11 ou 3.12 (versões mais recentes, como 3.13/3.14, podem ter
  incompatibilidades com dependências do `fio-plot`)
- [FIO](https://github.com/axboe/fio/releases) instalado no sistema
  (Windows: instalador `.msi`; Linux: `sudo apt install fio`)
- No Linux, o pacote de sistema `python3-tk` (Tkinter)

## Instalação (Windows)

```powershell
python --version
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Tkinter já vem com o Python no Windows (não precisa instalar nada
separado). Depois, instale o FIO:

1. Baixe o instalador oficial em
   https://github.com/axboe/fio/releases (arquivo `fio-X.XX-x64.msi`,
   disponível desde a versão 3.31).
2. Instale e reabra o terminal. Confirme com `fio --version`.

Não é necessário WSL nem Cygwin.

## Instalação (Linux / Linux Mint)

```bash
sudo apt update
sudo apt install fio python3-tk python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
fio --version
```

`python3-tk` é o pacote do Tkinter no Linux — sem ele o `import tkinter`
falha. (No Windows já vem incluso com o instalador do Python.)

## Execução

### Automática (recomendado)

**Windows** — dê 2 cliques em `setup_and_run.bat`:

```powershell
setup_and_run.bat
```

**Linux:**

```bash
chmod +x setup_and_run.sh   # uma única vez
./setup_and_run.sh
```

Cada script cria o ambiente virtual, instala as dependências do
`requirements.txt` e já abre a janela. Nas execuções seguintes, pula
direto para abrir o programa. Nenhum dos dois instala nada fora da
própria pasta do projeto.

### Manual

```bash
python -m venv venv

# Windows
venv\Scripts\Activate.ps1

# Linux
source venv/bin/activate

pip install -r requirements.txt
python gui.py
```

## Como usar

1. **Dependências**: mostra se `fio` e `fio-plot` foram encontrados.
2. **Configuração**: tamanho do arquivo de teste (padrão 1024 MiB),
   tempo por rodada (padrão 8 s) e quais iodepths testar (padrão
   `1 4 8 16`) — todos editáveis.
3. Botão **"Rodar benchmark e gerar gráficos"**: roda tudo numa thread
   separada, mostrando o progresso do FIO e do fio-plot em tempo real
   no log.
4. Abas com os 3 gráficos, exibidos dentro da própria janela assim que
   ficam prontos.

Com os valores padrão, o processo todo leva menos de 1 minuto.

## Estrutura do projeto

```
fioplot-gui/
├── gui.py                <- interface gráfica (Tkinter/ttk)
├── benchmark_core.py     <- lógica de benchmark e geração de gráficos
├── checks.py             <- verificação de dependências (fio / fio-plot)
├── requirements.txt
├── setup_and_run.bat     <- setup + execução automática (Windows)
├── setup_and_run.sh      <- setup + execução automática (Linux)
├── README.md
└── output/               <- gráficos gerados (.png)
```

`data/` e `venv/` não fazem parte do repositório — são recriados
automaticamente na primeira execução.

## Metodologia do benchmark

O benchmark testa leitura aleatória (`randread`) contra um arquivo de
1 GiB, em 4 filas de requisição diferentes (iodepth 1, 4, 8 e 16), 8
segundos cada. Todos os parâmetros são ajustáveis na própria interface.

## Por que o teste ficou maior (1 GiB / 8 s, e não 256 MB / 5 s)

Com `--direct=1`, o FIO ignora o cache do sistema operacional — mas
se o arquivo de teste é pequeno, os acessos aleatórios ficam
concentrados numa faixa pequena do arquivo, o que não reflete bem o
comportamento de um SSD/HD real sendo acessado de forma dispersa. Um
arquivo maior (1 GiB) dá aos acessos aleatórios uma área bem maior pra
se espalhar, produzindo números mais representativos — mantendo o
teste todo em menos de 1 minuto, viável de rodar ao vivo num seminário.
Os dois valores (tamanho e tempo) são ajustáveis direto na janela, caso
queira comparar o efeito de testes maiores/menores.

## Por que sem o `bench-fio`

O `bench-fio` (ferramenta que acompanha o pacote `fio-plot`) tenta
"limpar" o cache do sistema antes de cada rodada rodando, sem checar o
SO, o comando `echo 3 > /proc/sys/vm/drop_caches` — que só existe no
Linux. No Windows isso quebra com `FileNotFoundError: [WinError 2]`, e
não há flag para desativar (está fixo no código do `bench-fio`). Por
isso `benchmark_core.py` chama o `fio` diretamente e monta os arquivos
de saída no formato que o `fio-plot` espera — funciona igual nos dois
sistemas.

## Segurança do benchmark

- O alvo (`--filename`) é sempre um arquivo dentro de `data/`, nunca um disco ou partição física. Tamanho e
duração do teste são sempre finitos e configurados antes de cada
execução.


## O que representa cada gráfico

- **3D Bar Chart**: eixo X = iodepth, eixo Y = numjobs, altura da barra
  = IOPS médio (lê os `.json` do FIO).
- **Line Chart**: eixo X = tempo (segundos), eixo Y = IOPS, uma linha
  por iodepth (lê os `.log` do FIO).
- **Latency Histogram**: eixo X = faixas de latência (ns/us/ms), eixo Y
  = % das operações em cada faixa (lê a distribuição de latência do
  `.json`).

## Dependências

`fio-plot` (que traz matplotlib e numpy) e `Pillow` (usado tanto pelo
fio-plot quanto pela GUI, para exibir os PNGs nas abas). Tkinter é da
biblioteca padrão do Python; no Linux precisa do pacote de sistema
`python3-tk`.

## Decisões técnicas

- **Ioengine por sistema operacional.** `--direct=1` não é suportado
  pelo ioengine `sync` no Windows; o projeto detecta o SO e usa
  `windowsaio` no Windows e `sync` no Linux.
- **Captura de JSON via stdout.** O resultado do FIO é lido diretamente
  da saída padrão do processo (em memória) em vez de depender do FIO
  escrever o arquivo de resultado sozinho — evita inconsistências de
  sincronização em disco observadas no Windows.
- **Resolução de executáveis independente de ativação do venv.** Os
  scripts de setup rodam o Python do ambiente virtual diretamente, sem
  "ativar" o venv — por isso o projeto resolve os caminhos de `fio` e
  `fio-plot` também na pasta do próprio interpretador, e não só no
  PATH do sistema.
- **Interface responsiva.** O benchmark roda em uma thread separada da
  interface gráfica, com comunicação via fila (`queue.Queue`) — nenhuma
  chamada ao Tkinter é feita fora da thread principal.
