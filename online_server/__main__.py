"""Run with ``python -m online_server`` behind the deployment's TLS proxy."""
import argparse
import asyncio
import logging
import signal

from online_server import run


def main():
    parser = argparse.ArgumentParser(description='Saga2D authoritative online room server')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    async def start():
        task = asyncio.current_task()
        for signum in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_running_loop().add_signal_handler(signum, task.cancel)
        await run(args.host, args.port)

    try:
        asyncio.run(start())
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    main()
