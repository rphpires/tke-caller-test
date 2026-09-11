import flet as ft

def main(page: ft.Page):
    page.title = "AlertDialog examples"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    dlg = ft.AlertDialog(
        title=ft.Text("Hi, this is a non-modal dialog!"),
        # on_dismiss=lambda e: page.add(ft.Text("Non-modal dialog dismissed")),
    )

    page.add(
        ft.IconButton(
            icon=ft.icons.INFO_OUTLINE,
            on_click=lambda e: page.open(dlg)
        )
    )

ft.app(main)