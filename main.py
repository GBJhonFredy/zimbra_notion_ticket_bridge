# main.py
from ui.app import create_app
from ui.pet import PetWindow
from ui.pet_controller import PetController
from clients.notion_client import NotionTicketClient


def main():
    root = create_app()
    pet = PetWindow()
    notion_client = NotionTicketClient()
    PetController(notion_client, pet, poll_interval_ms=30_000)
    root.mainloop()


if __name__ == "__main__":
    main()
