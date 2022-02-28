import argparse
import asyncio
import struct
import ssl

import structlog
import aiofiles


log = structlog.get_logger()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("hid", help="HID Mouse Device to write to.")
    ssl = parser.add_subparsers(help="SSL Cert Info", dest="ssl")
    ssl_parser = ssl.add_parser("ssl", help="SSL Cert Config")
    ssl_parser.add_argument("cert", help="TLS Cert.")
    ssl_parser.add_argument("key", help="TLS Key.")
    ssl_parser.add_argument("ca", help="Server CA.")
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


def create_ssl_context(cert: str, key: str, ca: str) -> ssl.SSLContext:
    """Create SSL context."""

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.options |= ssl.OP_NO_TLSv1
    ssl_ctx.options |= ssl.OP_NO_TLSv1_1
    ssl_ctx.options |= ssl.OP_SINGLE_DH_USE
    ssl_ctx.options |= ssl.OP_SINGLE_ECDH_USE
    ssl_ctx.load_cert_chain(cert, keyfile=key)
    ssl_ctx.load_verify_locations(cafile=ca)
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.VerifyMode.CERT_REQUIRED
    ssl_ctx.set_ciphers("ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384")

    return ssl_ctx


async def amain():
    args = parse_args()

    hid = args.hid

    # If ssl enabled create ssl context.
    ssl_ctx = None
    ssl_args = args.ssl
    if args.ssl:
        ssl_ctx = create_ssl_context(*ssl_args)

    log.msg("creating server", host=args.host, port=args.port)

    async with aiofiles.open(hid, "wb+", buffering=0) as hid_fh:
        server = await asyncio.start_server(
            create_handler(hid_fh), args.host, args.port, ssl=ssl_ctx
        )
        async with server:
            await server.serve_forever()


def main():
    asyncio.run(amain())
