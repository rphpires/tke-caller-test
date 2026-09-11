import os
import sys

# Empacotado com --noconsole o PyInstaller deixa stdout/stderr em None, e qualquer
# print() dentro do app quebra. Redireciona antes de importar quem imprime.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from serial.tools import list_ports

from tke_functions import TRANSPORT_IP, TRANSPORT_SERIAL, ThyssenCommunication

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700

TEXTO_MCO = (
    "Mapeia qual MCO atende cada pavimento de destino.\n\n"
    "Formato: 1:4,6,7-18;2:20-99\n"
    "MCO 1 atende os pavimentos 4, 6 e 7 a 18; MCO 2 atende 20 a 99.\n\n"
    "Uma entrada sem faixa (ex.: 2) vale como padrão para qualquer pavimento "
    "não mapeado."
)

TEXTO_PAVIMENTO = (
    "Deslocamento subtraído dos andares de origem e destino antes do envio, "
    "para casar a numeração do controle de acesso com a do elevador.\n\n"
    "Ex.: ajuste -2 faz o andar 1 do controle virar 3 para o TKE."
)

TEXTO_DISCLAIMER = (
    "Este aplicativo não possui qualquer relação com os fabricantes de "
    "elevadores aqui citados."
)


def listar_portas_com():
    portas = sorted(p.device for p in list_ports.comports() if p.device.upper().startswith("COM"))
    return portas or [f"COM{i}" for i in range(1, 10)]


class App:
    def __init__(self, root):
        self.root = root
        self.tke = ThyssenCommunication()

        root.title("TKE | Chamada antecipada")
        root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        root.minsize(900, 600)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self._set_icone()
        self._build()

    def _set_icone(self):
        # Sem isto a janela fica com a pena padrão do Tk na barra de título.
        try:
            self.icone = tk.PhotoImage(file=os.path.join(self.base_dir, "assets", "logo_tke.png"))
            self.root.iconphoto(True, self.icone)
        except tk.TclError:
            pass

    # ------------------------------------------------------------- interface

    def _build(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        esquerda = ttk.Frame(outer)
        esquerda.grid(row=0, column=0, sticky="nw", padx=(0, 16))

        self._build_logo(esquerda)
        self._build_conexao(esquerda)
        self._build_chamada(esquerda)

        self._build_log(outer)
        self._build_rodape(outer)

    def _build_logo(self, parent):
        try:
            # subsample(2) reduz 270x119 -> 135x59 sem depender do Pillow.
            self.logo = tk.PhotoImage(file=os.path.join(self.base_dir, "assets", "logo_tke.png")).subsample(2, 2)
            ttk.Label(parent, image=self.logo).pack(anchor="w", pady=(0, 12))
        except tk.TclError:
            ttk.Label(parent, text="TKE", font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 12))

    def _build_conexao(self, parent):
        box = ttk.LabelFrame(parent, text="Conexão", padding=10)
        box.pack(fill="x", pady=(0, 12))

        ttk.Label(box, text="Tipo de conexão").grid(row=0, column=0, sticky="w")
        self.transporte = tk.StringVar(value=TRANSPORT_SERIAL)
        combo = ttk.Combobox(box, textvariable=self.transporte, state="readonly", width=42,
                             values=[TRANSPORT_SERIAL, TRANSPORT_IP])
        combo.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))
        combo.bind("<<ComboboxSelected>>", self.transporte_mudou)

        # Linha da serial e linha do IP ocupam a mesma célula; só uma fica visível.
        self.linha_serial = ttk.Frame(box)
        self.linha_serial.grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Label(self.linha_serial, text="Porta COM").grid(row=0, column=0, sticky="w")
        self.comm_port = tk.StringVar()
        portas = listar_portas_com()
        self.combo_porta = ttk.Combobox(self.linha_serial, textvariable=self.comm_port,
                                        state="readonly", width=12, values=portas)
        self.combo_porta.grid(row=1, column=0, sticky="w")
        ttk.Button(self.linha_serial, text="Atualizar", width=10,
                   command=self.atualizar_portas).grid(row=1, column=1, padx=(8, 0))

        self.linha_tcp = ttk.Frame(box)
        self.linha_tcp.grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Label(self.linha_tcp, text="IP do conversor").grid(row=0, column=0, sticky="w")
        self.tke_ip = tk.StringVar()
        ttk.Entry(self.linha_tcp, textvariable=self.tke_ip, width=20).grid(row=1, column=0, sticky="w")
        ttk.Label(self.linha_tcp, text="Porta TCP").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.tke_port = tk.StringVar(value="502")
        ttk.Entry(self.linha_tcp, textvariable=self.tke_port, width=10).grid(row=1, column=1, sticky="w", padx=(10, 0))
        self.linha_tcp.grid_remove()

        acoes = ttk.Frame(box)
        acoes.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self.botao_conexao = ttk.Button(acoes, text="Conectar", width=18, command=self.conectar)
        self.botao_conexao.grid(row=0, column=0, sticky="w")
        self.status = ttk.Label(acoes, text="Não conectado", foreground="#c0392b",
                                font=("Segoe UI", 10, "bold"))
        self.status.grid(row=0, column=1, sticky="w", padx=(12, 0))

    def _build_chamada(self, parent):
        box = ttk.LabelFrame(parent, text="Chamada", padding=10)
        box.pack(fill="x")

        self.gateway = tk.StringVar(value="1")
        self.mcos_dest = tk.StringVar()
        self.dispositivo = tk.StringVar()
        self.ajuste_pavimento = tk.StringVar()
        self.andar_origem = tk.StringVar()
        self.andar_destino = tk.StringVar()

        self.label_gateway = self._campo(box, 0, 0, "Endereço Gateway", self.gateway)
        self._campo(box, 0, 1, "MCOs de destino", self.mcos_dest,
                    ajuda=("MCOs de destino", TEXTO_MCO))
        self._campo(box, 1, 0, "Dispositivo", self.dispositivo)
        self._campo(box, 1, 1, "Ajuste de pavimento", self.ajuste_pavimento,
                    ajuda=("Ajuste de pavimento", TEXTO_PAVIMENTO))
        self._campo(box, 2, 0, "Andar Origem", self.andar_origem)
        self._campo(box, 2, 1, "Andar Destino", self.andar_destino)

        self.botao_chamada = ttk.Button(box, text="Fazer Chamada", command=self.fazer_chamada,
                                        state="disabled")
        self.botao_chamada.grid(row=3, column=0, columnspan=3, sticky="we", pady=(14, 0))

    def _campo(self, parent, linha, coluna, rotulo, variavel, ajuda=None):
        col = coluna * 2
        quadro = ttk.Frame(parent)
        quadro.grid(row=linha, column=col, sticky="w", padx=(0, 16), pady=(0, 8))

        topo = ttk.Frame(quadro)
        topo.pack(anchor="w")
        label = ttk.Label(topo, text=rotulo)
        label.pack(side="left")
        if ajuda:
            titulo, texto = ajuda
            ttk.Button(topo, text="?", width=2,
                       command=lambda: messagebox.showinfo(titulo, texto, parent=self.root)
                       ).pack(side="left", padx=(6, 0))

        ttk.Entry(quadro, textvariable=variavel, width=22).pack(anchor="w")
        return label

    def _build_log(self, parent):
        box = ttk.LabelFrame(parent, text="Logs da Conexão", padding=8)
        box.grid(row=0, column=1, sticky="nsew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)

        self.log = tk.Text(box, wrap="word", state="disabled", font=("Consolas", 9),
                           background="#fbfbfb", relief="flat")
        self.log.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(box, orient="vertical", command=self.log.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=barra.set)

    def _build_rodape(self, parent):
        rodape = ttk.Frame(parent)
        rodape.grid(row=1, column=0, columnspan=2, sticky="e", pady=(10, 0))

        link = ttk.Label(rodape, text="Desenvolvido por Raphael Pires",
                         foreground="#1a6fb5", cursor="hand2", font=("Segoe UI", 9, "underline"))
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: webbrowser.open(
            "https://www.linkedin.com/in/sp-raphael/?locale=en_US"))

        ttk.Button(rodape, text="?", width=2,
                   command=lambda: messagebox.showinfo("Sobre", TEXTO_DISCLAIMER, parent=self.root)
                   ).pack(side="left", padx=(8, 0))

    # ----------------------------------------------------------------- ações

    def atualizar_portas(self):
        portas = listar_portas_com()
        self.combo_porta.configure(values=portas)
        if self.comm_port.get() not in portas:
            self.comm_port.set("")

    def transporte_mudou(self, _evento=None):
        # Trocar de transporte derruba a conexão atual: os campos mudam de sentido.
        self.tke.disconnect()
        self.marcar_desconectado()

        usa_ip = self.transporte.get() == TRANSPORT_IP
        if usa_ip:
            self.linha_serial.grid_remove()
            self.linha_tcp.grid()
        else:
            self.linha_tcp.grid_remove()
            self.linha_serial.grid()
        # O endereço do gateway é o escravo Modbus nos dois casos: primeiro byte
        # do frame RTU, ou unit_id no MBAP. Mesmo campo, mesmo valor.
        self.label_gateway.configure(text="Endereço Gateway")

    def marcar_desconectado(self):
        self.status.configure(text="Não conectado", foreground="#c0392b")
        self.botao_chamada.configure(state="disabled")

    def escrever_log(self, texto):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("1.0", texto or "")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _em_thread(self, tarefa, ao_terminar):
        """O I/O serial/TCP pode levar segundos; fora da thread da UI ela congela."""
        self.botao_conexao.configure(state="disabled")
        self.botao_chamada.configure(state="disabled")

        def worker():
            try:
                resultado = tarefa()
            except Exception as ex:  # noqa: BLE001 - erro inesperado vai para o log
                resultado = ("Error: %s" % ex, False)
            self.root.after(0, lambda: ao_terminar(resultado))

        threading.Thread(target=worker, daemon=True).start()

    def conectar(self):
        if self.transporte.get() == TRANSPORT_IP:
            self.escrever_log(f"Trying to connect on {self.tke_ip.get()}:{self.tke_port.get()}...")
            tarefa = lambda: self.tke.open_gateway_ip(  # noqa: E731
                self.tke_ip.get(), self.tke_port.get(), self.gateway.get())
        else:
            self.escrever_log(f"Trying to connect on {self.comm_port.get()}...")
            tarefa = lambda: self.tke.open_terminal_loop(self.comm_port.get())  # noqa: E731

        self._em_thread(tarefa, self._conexao_terminou)

    def _conexao_terminou(self, resultado):
        reply, conectado = resultado
        self.botao_conexao.configure(state="normal")

        if conectado:
            self.status.configure(text="Conectado", foreground="#1e8449")
            self.botao_chamada.configure(state="normal")
        else:
            self.marcar_desconectado()

        self.escrever_log(reply)

    def fazer_chamada(self):
        dados = {
            "item_selecionado": self.transporte.get(),
            "gateway": self.gateway.get(),
            "ajuste_pavimento": self.ajuste_pavimento.get(),
            "mco_destino": self.mcos_dest.get(),
            "andar_origem": self.andar_origem.get(),
            "andar_destino": self.andar_destino.get(),
            "dispositivo": self.dispositivo.get(),
        }
        self._em_thread(lambda: self.tke.send_message(dados), self._chamada_terminou)

    def _chamada_terminou(self, resultado):
        self.botao_conexao.configure(state="normal")
        if self.tke.is_connected():
            self.botao_chamada.configure(state="normal")
        self.escrever_log(resultado if isinstance(resultado, str) else resultado[0])


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.tke.disconnect(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
