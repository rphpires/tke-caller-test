import flet as ft
import os
import webbrowser  # Para abrir o link no navegador
from tke_functions import ThyssenCommunication

tke = ThyssenCommunication()


def main(page: ft.Page):
    page.title = "TKE | Chamada antecipada"
    page.window_width = 700
    page.window_height = 700
    page.padding = 20

    # Dropdown com 4 itens
    dropdown = ft.Dropdown(
        width=400,
        label="Tipo de conexão",
        options=[
            ft.dropdown.Option("Modbus RTU - Serial"),
            # ft.dropdown.Option("Modbus - IP"),
            # ft.dropdown.Option("Modbus - Access Control")
        ],
    )

    # Remover quando outras opções estiverem disponíveis
    dropdown.value = "Modbus RTU - Serial"

    comm_port_list = ft.Dropdown(
        width=200,
        label="Porta COM",
        options=[
            ft.dropdown.Option("COM1"),
            ft.dropdown.Option("COM2"),
            ft.dropdown.Option("COM3"),
            ft.dropdown.Option("COM4"),
            ft.dropdown.Option("COM5"),
            ft.dropdown.Option("COM6"),
            ft.dropdown.Option("COM7"),
            ft.dropdown.Option("COM8"),
            ft.dropdown.Option("COM9")
        ],
    )

    # Campos de entrada
    gateway = ft.TextField(label="Endereço Gateway", width=200)
    ajuste_pavimento = ft.TextField(label="Ajuste de pavimento", width=200)
    mcos_dest = ft.TextField(label="MCOs de destino", width=200)
    comm_port = ft.TextField(label="Porta COM", width=200)
    andar_origem = ft.TextField(label="Andar Origem", width=200)
    andar_destino = ft.TextField(label="Andar Destino", width=200)
    dispositivo = ft.TextField(label="Dispositivo", width=200)

    conn_status = ft.Text("Não conectado", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.RED)

    # Valor padrão do gateway é 1
    gateway.value = 1

    # Campo para informações do backend
    info_backend = ft.TextField(
        # label="Mensagens",
        width=700,
        height=550,
        multiline=True,
        min_lines=25,
        max_lines=25,
        read_only=True
    )

    def fazer_chamada(e):
        # Função que será chamada quando o botão for pressionado
        dados = {
            "item_selecionado": dropdown.value,
            "gateway": gateway.value,
            "ajuste_pavimento": ajuste_pavimento.value,
            "mco_destino": mcos_dest.value,
            "com_port": comm_port_list.value,
            "andar_origem": andar_origem.value,
            "andar_destino": andar_destino.value,
            "dispositivo": dispositivo.value
        }
        print("Dados coletados:", dados)
        reply = tke.send_message(dados)
        info_backend.value = reply
        page.update()

    def conectar(e):
        info_backend.value = f"Trying to connect on {comm_port_list.value}..."
        page.update()

        reply, conected = tke.open_terminal_loop(comm_port_list.value)

        # conected = True
        if conected:
            conn_status.value = "Conectado"
            conn_status.color = ft.Colors.GREEN

            botao_chamada.disabled = False
            botao_chamada.tooltip = None

        info_backend.value = reply
        page.update()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "assets\\logo_tke.png")

    # Para imagem local (arquivo no seu computador)
    logo_local = ft.Image(
        src=logo_path,
        width=130,  # largura em pixels
        height=130,  # altura em pixels
        fit=ft.ImageFit.CONTAIN  # mantém a proporção da imagem
    )

    logo_container = ft.Container(
        content=logo_local,
        alignment=ft.alignment.top_left,
        margin=ft.margin.only(left=20, top=0)  # 20 pixels de margem à esquerda e topo
    )
    
    dlg_mco = ft.AlertDialog(
        title=ft.Text("Texto explicando configuração do MCO", size=18)
    )

    info_mco = ft.IconButton(
        icon=ft.icons.INFO_OUTLINE,
        on_click=lambda e: page.open(dlg_mco)
    )

    dlg_pavimento = ft.AlertDialog(
        title=ft.Text("Texto ajuste de pavimento")
    )

    info_pavimento = ft.IconButton(
        icon=ft.icons.INFO_OUTLINE,
        on_click=lambda e: page.open(dlg_pavimento)
    )

    # Botão de fazer chamada
    botao_chamada = ft.ElevatedButton(
        text="Fazer Chamada",
        on_click=fazer_chamada,
        width=410,
        disabled=True,
        tooltip="COM Port not connected"
    )

    botao_conexao = ft.ElevatedButton(
        text="Conectar",
        on_click=conectar,
        width=200,
    )

    connection_row = ft.Row(
        controls=[
            comm_port_list,
            ft.VerticalDivider(width=10),
            conn_status,
        ],
        spacing=5,
        alignment=ft.MainAxisAlignment.START,
    )

    row_1 = ft.Row(
        controls=[
            gateway,
            ft.VerticalDivider(width=10),
            mcos_dest,
            info_mco
        ],
        spacing=5,
        alignment=ft.MainAxisAlignment.START,
    )

    row_2 = ft.Row(
        controls=[
            dispositivo,
            ft.VerticalDivider(width=10),
            ajuste_pavimento,
            info_pavimento
        ],
        spacing=5,
        alignment=ft.MainAxisAlignment.START,
    )

    row_3 = ft.Row(
        controls=[
            andar_origem,
            ft.VerticalDivider(width=10),
            andar_destino,
        ],
        spacing=5,
        alignment=ft.MainAxisAlignment.START,
    )

    # Criando o layout em duas colunas
    coluna_esquerda = ft.Column(
        controls=[
            dropdown,
            ft.Divider(),
            connection_row,
            botao_conexao,
            ft.Divider(),
            row_1,
            row_2,
            row_3,
            ft.Divider(),
            botao_chamada,
        ],
        spacing=10,
    )

    coluna_direita = ft.Column(
        controls=[
            ft.Text("Logs da Conexão", size=20, weight=ft.FontWeight.BOLD),
            info_backend,
        ],
        spacing=10,
    )

    # Criando um layout vertical com logo e conteúdo principal
    layout_esq = ft.Column(
        controls=[
            logo_container,
            coluna_esquerda
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.START,
    )

    layout = ft.Row(
        controls=[
            layout_esq,
            ft.VerticalDivider(width=30),
            coluna_direita,
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.START,
    )

    # Link no canto inferior direito
    def abrir_link(e):
        webbrowser.open("https://www.linkedin.com/in/sp-raphael/?locale=en_US")  # Substitua pelo link desejado

    link_desenvolvimento = ft.TextButton(
        content=ft.Text(
            "Desenvolvido por Raphael Pires",  # Substitua pelo texto desejado
            size=12,
            color=ft.Colors.BLUE,
            weight=ft.FontWeight.W_600,
            style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
        ),
        on_click=abrir_link,  # Agora funciona
    )

    container_link = ft.Container(
        content=link_desenvolvimento,
        alignment=ft.alignment.bottom_right,
        # margin=ft.margin.only(right=20, bottom=20),
    )

    # dlg_mco = ft.AlertDialog(
    #     title=ft.Text("Texto explicando configuração do MCO", size=18)
    # )

    info_dev = ft.IconButton(
        icon=ft.icons.INFO_OUTLINE,
        on_click=lambda e: page.open(
            ft.AlertDialog(
                title=ft.Text("Este aplicativo não possui qualquer relação com os fabricantes de elevadores aqui citados.", size=18)
            )
        )
    )

    # Agrupa o ícone info_mco e o link de desenvolvimento em uma linha
    footer_row = ft.Row(
        controls=[
            container_link,  # Link de desenvolvimento
            info_dev,  # Ícone de informação sobre o MCO
        ],
        alignment=ft.MainAxisAlignment.END,  # Alinha a linha no canto inferior direito
        spacing=2,  # Espaçamento entre os componentes
    )

    # Adicionando o layout e o link à página
    page.add(layout, footer_row)

if __name__ == "__main__":
    ft.app(target=main)