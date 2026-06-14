try:
    from .main import run
except ImportError:
    from ringcentral_csv_editor.main import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
