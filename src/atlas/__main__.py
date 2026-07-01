from atlas.cli import app

def main():
    try:
        app()
    except Exception as e:
        print(f"✗ {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()