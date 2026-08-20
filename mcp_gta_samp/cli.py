import argparse
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .headless import HeadlessClient
from .mcp_server import create_mcp_server
from .openmp import OpenMpServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-gta-samp",
        description="AI-native open.mp/SA-MP testing MCP server (local/owned servers only).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to a JSON config file with an 'executable' key.",
    )
    parser.add_argument("--client-executable", type=Path)
    parser.add_argument("--client-arg", action="append", default=[])
    parser.add_argument("--gamemode-source", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    server = OpenMpServer(config)
    client = None
    if args.client_executable:
        client = HeadlessClient(str(args.client_executable), args.client_arg)
    app = create_mcp_server(server, client=client, gamemode_source=args.gamemode_source)
    try:
        app.run("stdio")
    finally:
        if client is not None:
            client.stop()
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
