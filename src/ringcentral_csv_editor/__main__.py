
from .main import RingCentralCSVApp, on_startup

def main() -> None:
    on_startup()
    RingCentralCSVApp().run()

if __name__ == "__main__":
    main()
