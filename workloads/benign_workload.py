import argparse
import hashlib
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['steady', 'phase-change'], default='steady')
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--seed', type=int, default=7)
    a = p.parse_args()
    end = time.monotonic() + a.seconds
    block = bytearray((i * 31 + a.seed) % 251 for i in range(1024 * 1024))
    digest = b'cache-project'
    while time.monotonic() < end:
        if a.mode == 'steady':
            for i in range(0, len(block), 4096):
                block[i] = (block[i] + 1) % 251
            digest = hashlib.sha256(digest + block[:65536]).digest()
        else:
            elapsed = a.seconds - max(0, end - time.monotonic())
            if elapsed < a.seconds / 2:
                for i in range(0, len(block), 16384):
                    block[i] = (block[i] + 1) % 251
            else:
                for i in range(0, len(block), 256):
                    block[i] = (block[i] + 3) % 251
                digest = hashlib.sha512(digest + block[:262144]).digest()
    print(digest.hex()[:16], flush=True)


if __name__ == '__main__':
    main()
