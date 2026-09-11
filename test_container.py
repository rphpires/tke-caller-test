import flet as ft
import os

def main(page: ft.Page):
    page.title = "Layout App"
    page.window_width = 800
    page.window_height = 600
    page.padding = 20

    # Logo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_filename = "assets\\logo_tke.png"  # Substitua pelo nome do seu arquivo de logo
    logo_path = os.path.join(current_dir, logo_filename)

    logo = ft.Image(
        src=logo_path,
        width=100,
        height=100,
        fit=ft.ImageFit.CONTAIN
    )

    # Lista de elementos (exemplo com TextField)
    input_1 = ft.TextField(label="Campo 1", width=300)
    input_2 = ft.TextField(label="Campo 2", width=300)
    input_3 = ft.TextField(label="Campo 3", width=300)
    input_4 = ft.TextField(label="Campo 4", width=300)

    # Botão
    botao = ft.ElevatedButton(
        text="Botão",
        width=300
    )

    # Área de logs
    logs_area = ft.TextField(
        label="Logs",
        width=400,
        height=500,
        multiline=True,
        read_only=True
    )

    # Coluna da esquerda (logo + inputs + botão)
    coluna_esquerda = ft.Column(
        controls=[
            logo,
            ft.Divider(),
            input_1,
            input_2,
            input_3,
            input_4,
            ft.Divider(),
            botao
        ],
        spacing=20,
    )

    # Coluna da direita (logs)
    coluna_direita = ft.Column(
        controls=[
            ft.Text("Logs", size=20, weight=ft.FontWeight.BOLD),
            logs_area
        ]
    )

    # Layout principal
    layout = ft.Row(
        controls=[
            coluna_esquerda,
            ft.VerticalDivider(width=30),
            coluna_direita
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.START
    )

    page.add(layout)

if __name__ == "__main__":
    ft.app(target=main)