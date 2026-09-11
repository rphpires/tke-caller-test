import flet as ft
import webbrowser  # Biblioteca para abrir URLs no navegador

def main(page: ft.Page):
    page.title = "Abrir Link no Navegador"
    page.window_width = 400
    page.window_height = 300
    page.padding = 20

    def abrir_link(e):
        webbrowser.open("https://www.linkedin.com/in/sp-raphael/")  # Substitua pelo link desejado

    link_desenvolvimento = ft.TextButton(
        content=ft.Text(
            "Desenvolvido por Raphael Pires",  # Substitua pelo texto desejado
            size=12,
            color=ft.colors.BLUE,
            weight=ft.FontWeight.W_600,
            style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
        ),
        on_click=abrir_link,  # Agora funciona
    )
    container_link = ft.Container(
        content=link_desenvolvimento,
        alignment=ft.alignment.bottom_right,
        margin=ft.margin.only(right=20, bottom=20),
    )

    # Adicionando o layout e o link à página
    page.add(layout, container_link)

if __name__ == "__main__":
    ft.app(target=main)

if __name__ == "__main__":
    ft.app(target=main)