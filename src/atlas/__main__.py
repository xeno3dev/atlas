from atlas.cli import app
from atlas.errors import AtlasError

def main():
    try:
        app()
    except AtlasError as e:
        print(f"✗ {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()