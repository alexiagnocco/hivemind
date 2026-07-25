from __future__ import annotations

import sys


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    from hivemind.server import mcp

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
