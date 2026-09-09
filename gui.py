"""
Interface gráfica (Tkinter + ttk) do Exercício 1 (ORI).

Roda em Windows e Linux sem alterações — Tkinter é parte da biblioteca
padrão do Python nos dois sistemas (no Linux, se não vier pré-instalado,
basta 'sudo apt install python3-tk').

O que a janela faz:
  1. Verifica dependências (fio, fio-plot) e mostra o status.
  2. Deixa configurar tamanho do arquivo de teste, tempo por rodada e
     quais iodepths testar.
  3. Roda o benchmark (FIO) e gera os 3 gráficos com fio-plot, mostrando
     o progresso em tempo real numa área de log.
  4. Exibe os 3 gráficos gerados em abas, dentro da própria janela.

O benchmark roda numa thread separada para a janela não travar (ficar
"não respondendo") enquanto o FIO está rodando.
"""

import pathlib
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

import checks
import benchmark_core as core


class FioPlotApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.master = master
        self.master.title("Exercício 1 (ORI) — Benchmark FIO + fio-plot")
        self.master.geometry("880x640")
        self.grid(sticky="nsew")
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.result_queue: "queue.Queue[tuple]" = queue.Queue()
        self.worker_thread = None
        self.photo_refs = []  # evita que as imagens sejam coletadas pelo garbage collector

        self._build_dependency_panel()
        self._build_config_panel()
        self._build_action_panel()
        self._build_log_panel()
        self._build_results_panel()

        self._check_dependencies()
        self.after(150, self._poll_queues)

    # ---------- Painel de dependências ----------

    def _build_dependency_panel(self):
        frame = ttk.LabelFrame(self, text="Dependências", padding=8)
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.dep_labels = {}
        for i, name in enumerate(("fio", "fio-plot")):
            ttk.Label(frame, text=f"{name}:").grid(row=0, column=i * 2, sticky="w", padx=(0, 4))
            lbl = ttk.Label(frame, text="verificando...", foreground="gray")
            lbl.grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 24))
            self.dep_labels[name] = lbl

    def _check_dependencies(self):
        results = checks.run_all_checks()
        all_ok = True
        for name, ok, info in results:
            lbl = self.dep_labels[name]
            if ok:
                lbl.config(text="OK", foreground="#1a7f37")
            else:
                lbl.config(text="FALTANDO", foreground="#c0392b")
                all_ok = False
        if not all_ok:
            messagebox.showwarning(
                "Dependência faltando",
                "Alguma dependência não foi encontrada. Veja o README para instalar "
                "o FIO e o fio-plot antes de rodar o benchmark.",
            )

    # ---------- Painel de configuração ----------

    def _build_config_panel(self):
        frame = ttk.LabelFrame(self, text="Configuração do benchmark", padding=8)
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Tamanho do arquivo de teste (MiB):").grid(row=0, column=0, sticky="w")
        self.size_var = tk.IntVar(value=core.DEFAULT_SIZE_MB)
        ttk.Entry(frame, textvariable=self.size_var, width=10).grid(row=0, column=1, sticky="w", padx=(4, 24))

        ttk.Label(frame, text="Tempo por rodada (segundos):").grid(row=0, column=2, sticky="w")
        self.runtime_var = tk.IntVar(value=core.DEFAULT_RUNTIME_S)
        ttk.Entry(frame, textvariable=self.runtime_var, width=6).grid(row=0, column=3, sticky="w", padx=(4, 24))

        ttk.Label(frame, text="Iodepths (separados por espaço):").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.iodepths_var = tk.StringVar(value=" ".join(str(d) for d in core.DEFAULT_IODEPTHS))
        ttk.Entry(frame, textvariable=self.iodepths_var, width=20).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=(4, 24), pady=(6, 0)
        )

        note = (
            "Arquivo maior + mais tempo por rodada dá ao FIO uma área maior pra "
            "espalhar os acessos aleatórios, gerando números mais representativos "
            "de um SSD/HD real (o padrão anterior, 256 MB / 5 s, era pequeno demais)."
        )
        ttk.Label(frame, text=note, wraplength=820, foreground="gray").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )

    # ---------- Painel de ações ----------

    def _build_action_panel(self):
        frame = ttk.Frame(self)
        frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.run_button = ttk.Button(frame, text="Rodar benchmark e gerar gráficos", command=self._on_run_clicked)
        self.run_button.grid(row=0, column=0, sticky="w")

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=300)
        self.progress.grid(row=0, column=1, sticky="w", padx=(12, 0))

    # ---------- Painel de log ----------

    def _build_log_panel(self):
        frame = ttk.LabelFrame(self, text="Log", padding=4)
        frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)

        self.log_text = tk.Text(frame, height=10, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scrollbar.set)

    # ---------- Painel de resultados (abas com os gráficos) ----------

    def _build_results_panel(self):
        frame = ttk.LabelFrame(self, text="Gráficos gerados", padding=4)
        frame.grid(row=4, column=0, columnspan=2, sticky="nsew")
        self.rowconfigure(4, weight=2)

        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True)

        self.image_labels = {}
        for title in ("3d_bar_chart", "line_chart", "latency_histogram"):
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title.replace("_", " ").title())
            lbl = ttk.Label(tab, text="(ainda não gerado)")
            lbl.pack(fill="both", expand=True)
            self.image_labels[title] = lbl

    # ---------- Lógica de execução ----------

    def _log(self, message: str) -> None:
        """Thread-safe: apenas enfileira, quem escreve no widget é a thread principal."""
        self.log_queue.put(message)

    def _poll_queues(self):
        """
        Roda periodicamente na thread principal (agendado via self.after).
        É o ÚNICO lugar que lê as filas e mexe nos widgets — a thread de
        trabalho (_run_pipeline) só põe coisas nas filas, nunca chama
        métodos do Tkinter diretamente. Isso evita problemas de
        concorrência entre threads no Tkinter.
        """
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass

        try:
            while True:
                kind, payload = self.result_queue.get_nowait()
                self.progress.stop()
                self.run_button.config(state="normal")
                if kind == "success":
                    self._show_results(payload)
                elif kind == "error":
                    messagebox.showerror("Erro no benchmark", payload)
        except queue.Empty:
            pass

        self.after(150, self._poll_queues)

    def _on_run_clicked(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        try:
            size_mb = int(self.size_var.get())
            runtime_s = int(self.runtime_var.get())
            iodepths = [int(x) for x in self.iodepths_var.get().split()]
            if size_mb <= 0 or runtime_s <= 0 or not iodepths:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Configuração inválida", "Confira o tamanho, o tempo e os iodepths informados.")
            return

        self.run_button.config(state="disabled")
        self.progress.start(12)
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self.worker_thread = threading.Thread(
            target=self._run_pipeline, args=(size_mb, runtime_s, iodepths), daemon=True
        )
        self.worker_thread.start()

    def _run_pipeline(self, size_mb: int, runtime_s: int, iodepths: list) -> None:
        """
        Roda inteiramente na thread de trabalho. Nunca chama métodos do
        Tkinter diretamente daqui — só escreve nas filas (log_queue,
        result_queue), que a thread principal consome em _poll_queues.
        """
        try:
            data_dir = core.run_benchmark(size_mb, runtime_s, iodepths, log=self._log)
            outputs = core.generate_plots(data_dir, iodepths, log=self._log)
            self._log("\nConcluído! Gráficos salvos em output/.")
            self.result_queue.put(("success", outputs))
        except Exception as exc:  # noqa: BLE001 — queremos mostrar qualquer erro na GUI
            self._log(f"\nERRO: {exc}")
            self.result_queue.put(("error", str(exc)))

    def _show_results(self, outputs: dict) -> None:
        self.photo_refs.clear()
        for name, path in outputs.items():
            image = Image.open(path)
            image.thumbnail((760, 420))
            photo = ImageTk.PhotoImage(image)
            self.photo_refs.append(photo)  # mantém referência viva
            self.image_labels[name].config(image=photo, text="")


def main():
    root = tk.Tk()
    FioPlotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
