# main.py de tu bridge
from ui.app import create_app


def main():
    root = create_app()
    root.mainloop()


if __name__ == "__main__":
    main()
