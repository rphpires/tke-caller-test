import flet as ft
import os
from tke_functions import ThyssenCommunication


class ElevatorInterface:
    def __init__(self, page: ft.Page):
        self.page = page
        self.tke = ThyssenCommunication()
        self.setup_page()
        self.build_components()

    def setup_page(self):
        """Configura as propriedades da página."""
        self.page.title = "TKE | Interface de Chamadas"
        self.page.window_width = 700
        self.page.window_height = 700
        self.page.padding = 20

    def build_components(self):
        """Cria todos os componentes da interface."""
        self.dropdown = ft.Dropdown(
            width=400,
            label="Tipo de conexão",
            options=[ft.dropdown.Option("Modbus RTU - Serial")],
            on_change=self.dropdown_changed
        )

        self.gateway = ft.TextField(label="Endereço Gateway", width=200, value="1")
        self.ajuste_pavimento = ft.TextField(label="Ajuste de pavimento", width=200)
        self.mcos_dest = ft.TextField(label="MCOs de destino", width=200)
        self.comm_port = ft.TextField(label="Porta COM", width=200)
        self.andar_origem = ft.TextField(label="Andar Origem", width=200)
        self.andar_destino = ft.TextField(label="Andar Destino", width=200)
        self.dispositivo = ft.TextField(label="Dispositivo", width=200)

        self.conn_status = ft.Text("Não conectado", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.RED)

        self.info_backend = ft.TextField(
            label="Informações do Sistema", width=700, height=600, multiline=True,
            min_lines=25, max_lines=25, read_only=True
        )

        self.botao_chamada = ft.ElevatedButton(
            text="Fazer Chamada", on_click=self.fazer_chamada, width=410, disabled=True, tooltip="COM Port not connected"
        )

        self.botao_conexao = ft.ElevatedButton(
            text="Conectar", on_click=self.conectar, width=200
        )

        self.load_logo()
        self.build_layout()

    def load_logo(self):
        """Carrega a imagem do logo."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_filename = "assets\\logo_tke.png"
        logo_path = os.path.join(current_dir, logo_filename)

        self.logo = ft.Image(
            src=logo_path, width=130, height=130, fit=ft.ImageFit.CONTAIN
        )

    def build_layout(self):
        """Monta o layout da interface."""
        self.layout = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Container(content=self.logo, alignment=ft.alignment.top_left, margin=ft.margin.only(left=20, top=10)),
                        self.dropdown,
                        ft.Divider(),
                        ft.Row([self.comm_port, self.conn_status], spacing=5),
                        self.botao_conexao,
                        ft.Divider(),
                        ft.Row([self.gateway, self.mcos_dest]),
                        ft.Row([self.dispositivo, self.ajuste_pavimento]),
                        ft.Row([self.andar_origem, self.andar_destino]),
                        ft.Divider(),
                        self.botao_chamada,
                    ],
                    spacing=10
                ),
                ft.VerticalDivider(width=30),
                ft.Column(
                    controls=[
                        ft.Text("Log do Sistema", size=20, weight=ft.FontWeight.BOLD),
                        self.info_backend,
                    ],
                    spacing=10
                ),
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.START,
        )

        self.page.add(self.layout)

    def dropdown_changed(self, e):
        def dropdown_changed(e):
            if dropdown.value in ["Atlas Schindler"]:
                _elv_logo = 'atlas'
            else:
                _elv_logo = 'tke'

            logo_local.src = os.path.join(current_dir, f"assets\\logo_{_elv_logo}.png")
            page.update()

    def fazer_chamada(self, e):
        """Executa a ação de chamada."""
        dados = {
            "item_selecionado": self.dropdown.value,
            "gateway": self.gateway.value,
            "ajuste_pavimento": self.ajuste_pavimento.value,
            "mco_destino": self.mcos_dest.value,
            "com_port": f"COM{self.comm_port.value}",
            "andar_origem": self.andar_origem.value,
            "andar_destino": self.andar_destino.value,
            "dispositivo": self.dispositivo.value
        }
        print("Dados coletados:", dados)
        reply = self.tke.send_message(dados)
        self.info_backend.value = reply
        self.page.update()

    def conectar(self, e):
        """Tenta conectar e atualiza o status."""
        self.info_backend.value = f"Tentando conectar na COM{self.comm_port.value}..."
        self.page.update()

        reply, connected = self.tke.open_terminal_loop(self.comm_port.value)

        if connected:
            self.conn_status.value = "Conectado"
            self.conn_status.color = ft.colors.GREEN
            self.botao_chamada.disabled = False
            self.botao_chamada.tooltip = None

        self.info_backend.value = reply
        self.page.update()


def main(page: ft.Page):
    app = ElevatorInterface(page)
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
