"""Undetected-error rate of ARDOP 1.0.2.9's per-carrier CRC (poly constant &H8810) vs true CRC-16-CCITT (&H1021),
same bit-serial algorithm as Globals.vb GenCRC16FrameType/CheckCRC16FrameType."""
import random
def crc(data, poly):
    reg = 0xFFFF
    for b in data:
        for i in range(7, -1, -1):
            bit = (b >> i) & 1
            msb = reg & 0x8000
            reg = (reg << 1 | bit) & 0xFFFF
            if msb: reg ^= poly
    return reg
def trial(poly, n_err_syms, rng, L=1+128):
    data = bytes(rng.randrange(256) for _ in range(L))
    c = crc(data, poly)
    bad = bytearray(data)
    # n symbol (nibble) errors at random nibble positions, random wrong nibble
    pos = rng.sample(range(2*L), n_err_syms)
    for p in pos:
        sh = 4 if p % 2 == 0 else 0
        old = (bad[p//2] >> sh) & 0xF
        new = rng.choice([v for v in range(16) if v != old])
        bad[p//2] = (bad[p//2] & ~(0xF << sh)) | (new << sh)
    return crc(bytes(bad), poly) == c
rng = random.Random(1)
N = 200000
for poly, name in ((0x8810, "ARDOP 1.0.2.9 (&H8810)"), (0x1021, "CRC-16-CCITT (&H1021)")):
    for k in (1, 2, 4):
        miss = sum(trial(poly, k, rng) for _ in range(N))
        print(f"{name:26s} {k} symbol error(s): {miss}/{N} undetected = 1 in {N/miss:,.0f}" if miss else f"{name:26s} {k} symbol error(s): 0/{N} undetected")
