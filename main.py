# main.py
# Punto de entrada de la aplicacion.
# Este archivo solo orquesta la inicializacion de componentes principales.
from ui.app import create_app
from ui.pet import PetWindow
from ui.pet_controller import PetController
from clients.notion_client import NotionTicketClient


def main():
    # Crea la ventana principal (dashboard Tkinter con monitor y stream de eventos).
    root = create_app()
    # Crea la mascota flotante en una ventana secundaria.
    pet = PetWindow()
    # Inicializa el cliente Notion (valida token y database id en el constructor).
    notion_client = NotionTicketClient()
    # Inicia el controlador de notificaciones de la mascota:
    # - consulta Notion cada 30s
    # - rota mensajes cada 20s (valor por defecto dentro del controlador)
    PetController(notion_client, pet, poll_interval_ms=30_000)
    # Arranca el loop de eventos de Tkinter; desde aqui la app queda escuchando UI/eventos.
    root.mainloop()


if __name__ == "__main__":
    # Ejecuta main solo cuando se corre este archivo directamente.
    main()
