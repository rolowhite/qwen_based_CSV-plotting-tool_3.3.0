from .bootstrap import prepare_runtime

if not prepare_runtime():
    raise SystemExit(1)

from .app import main

main()
