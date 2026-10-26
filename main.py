"""Start CSV Plot Studio; missing application packages are installed automatically."""
from plotstudio.bootstrap import prepare_runtime

if __name__ == "__main__":
    if not prepare_runtime():
        raise SystemExit(1)
    from plotstudio.app import main

    main()
