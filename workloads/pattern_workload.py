#!/usr/bin/env python3
"""Safe deterministic workload generator; uses private memory only."""
import argparse, hashlib, random, time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pattern', choices=['sequential','strided','random','hash','transition'], required=True)
    p.add_argument('--seconds', type=float, default=10)
    p.add_argument('--size-kb', type=int, default=1024)
    p.add_argument('--stride', type=int, default=64)
    p.add_argument('--seed', type=int, default=7)
    a = p.parse_args()
    if a.size_kb < 16 or a.stride < 1 or a.seconds <= 0:
        raise SystemExit('invalid size, stride, or duration')
    buf = bytearray((i * 17 + a.seed) % 251 for i in range(a.size_kb * 1024))
    rng = random.Random(a.seed)
    indices = list(range(0, len(buf), max(1, a.stride)))
    rng.shuffle(indices)
    digest = b'pattern-workload'
    end = time.monotonic() + a.seconds
    while time.monotonic() < end:
        elapsed = a.seconds - max(0.0, end - time.monotonic())
        mode = a.pattern
        if mode == 'transition':
            mode = 'sequential' if elapsed < a.seconds / 2 else 'random'
        if mode == 'sequential':
            for i in range(0, len(buf), 64):
                buf[i] = (buf[i] + 1) % 251
        elif mode == 'strided':
            for i in range(0, len(buf), a.stride):
                buf[i] = (buf[i] + 3) % 251
        elif mode == 'random':
            for i in indices[:max(1, len(indices) // 2)]:
                buf[i] = (buf[i] + 5) % 251
        elif mode == 'hash':
            digest = hashlib.sha512(digest + buf[: min(len(buf), 262144)]).digest()
        if mode != 'hash':
            digest = hashlib.sha256(digest + buf[: min(len(buf), 65536)]).digest()
    print(digest.hex()[:16], flush=True)


if __name__ == '__main__':
    main()
