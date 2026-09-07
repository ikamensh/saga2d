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
    parser.add_argument('--state-dir', help='Private directory for persistent room checkpoints')
    parser.add_argument('--room-ttl', type=float, default=900, help='Disconnected room retention in seconds')
    parser.add_argument('--max-rooms', type=int, default=64)
    parser.add_argument('--max-connections', type=int, default=128)
    parser.add_argument('--trusted-proxy', action='store_true',
                        help='Trust X-Forwarded-For from a loopback reverse proxy only')
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    async def start():
        task = asyncio.current_task()
        for signum in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_running_loop().add_signal_handler(signum, task.cancel)
        await run(args.host, args.port, state_dir=args.state_dir, room_ttl=args.room_ttl,
                  max_rooms=args.max_rooms, max_connections=args.max_connections,
                  trusted_proxy=args.trusted_proxy)

    try:
        asyncio.run(start())
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    main()
