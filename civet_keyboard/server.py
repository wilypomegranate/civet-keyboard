import argparse
import asyncio
import struct

import structlog
import aiofiles


log = structlog.get_logger()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("hid", help="HID Mouse Device to write to.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", default="5002")
    return parser.parse_args()


def create_handler(hid_fh):
    async def handle_key(reader, _):
        while True:
            keystroke = await reader.read(8)
            modifier, _, *keys = struct.unpack("<bbbbbbbb", keystroke)
            log.msg("keystroke sent", modifier=modifier, keys=keys)
            await hid_fh.write(keystroke)

    return handle_key


async def amain():
    args = parse_args()

    hid = args.hid

    log.msg("creating server", host=args.host, port=args.port)

    async with aiofiles.open(hid, "wb+", buffering=0) as hid_fh:
        server = await asyncio.start_server(
            create_handler(hid_fh), args.host, args.port
        )
        async with server:
            await server.serve_forever()


def main():
    asyncio.run(amain())
