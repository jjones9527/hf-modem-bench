#!/usr/bin/env python3
"""Check a Winlink Express partial (Partials/<MID>.bin) against the payload that was sent.

A partial holds the B2F compressed stream received so far: CRC16 (2 bytes), uncompressed
length (4 bytes, little-endian), then LZHUF data (Okumura, N=2048, F=60, THRESHOLD=2).
This decodes it and reports how far the attachment matches the original file, which
tells a corrupted transfer from one that simply stopped.

    python3 scripts/check_partial.py <MID>.bin payloads/Text_50KB/<file>.txt
"""
import struct
import sys

N, F, TH = 2048, 60, 2
N_CHAR = 256 - TH + F; T = N_CHAR * 2 - 1; R = T - 1; MAX_FREQ = 0x8000
d_code = bytes([0]*32 + [c for c in range(1,4) for _ in range(16)] + [c for c in range(4,12) for _ in range(8)]
               + [c for c in range(12,24) for _ in range(4)] + [c for c in range(24,48) for _ in range(2)] + list(range(48,64)))
assert len(d_code)==256
d_len = bytes([3]*32+[4]*48+[5]*64+[6]*48+[7]*48+[8]*16)
class EOFErr(Exception): pass
def decode(data, outlen):
    freq=[0]*(T+1); prnt=[0]*(T+N_CHAR); son=[0]*T
    for i in range(N_CHAR): freq[i]=1; son[i]=i+T; prnt[i+T]=i
    i,j=0,N_CHAR
    while j<=R:
        freq[j]=freq[i]+freq[i+1]; son[j]=i; prnt[i]=prnt[i+1]=j; i+=2; j+=1
    freq[T]=0xffff; prnt[R]=0
    pos=[0]; buf=[0]; blen=[0]
    def getbit():
        if blen[0]<=8:
            if pos[0]>=len(data): 
                if blen[0]==0: raise EOFErr
                c=0
            else: c=data[pos[0]]; pos[0]+=1
            buf[0]|=c<<(8-blen[0]); blen[0]+=8
        b=(buf[0]>>15)&1; buf[0]=(buf[0]<<1)&0xffff; blen[0]-=1; return b
    def getbyte():
        v=0
        for _ in range(8): v=(v<<1)|getbit()
        return v
    def reconst():
        j=0
        for i in range(T):
            if son[i]>=T: freq[j]=(freq[i]+1)//2; son[j]=son[i]; j+=1
        i=0; j=N_CHAR
        while j<T:
            k=i+1; f=freq[j]=freq[i]+freq[k]
            k=j-1
            while f<freq[k]: k-=1
            k+=1
            freq[k+1:j+1]=freq[k:j]; freq[k]=f
            son[k+1:j+1]=son[k:j]; son[k]=i
            i+=2; j+=1
        for i in range(T):
            k=son[i]
            if k>=T: prnt[k]=i
            else: prnt[k]=prnt[k+1]=i
    def update(c):
        if freq[R]==MAX_FREQ: reconst()
        c=prnt[c+T]
        while True:
            freq[c]+=1; k=freq[c]; l=c+1
            if k>freq[l]:
                while k>freq[l+1]: l+=1
                freq[c]=freq[l]; freq[l]=k
                i=son[c]; prnt[i]=l
                if i<T: prnt[i+1]=l
                j=son[l]; son[l]=i
                prnt[j]=c
                if j<T: prnt[j+1]=c
                son[c]=j; c=l
            c=prnt[c]
            if c==0: break
    def dchar():
        c=son[R]
        while c<T: c=son[c+getbit()]
        c-=T; update(c); return c
    def dpos():
        i=getbyte(); c=d_code[i]<<6; j=d_len[i]-2
        while j: i=(i<<1)|getbit(); j-=1
        return c|(i&0x3f)
    text=bytearray(b" "*(N+F-1)); r=N-F; out=bytearray()
    try:
        while len(out)<outlen:
            c=dchar()
            if c<256:
                out.append(c); text[r]=c; r=(r+1)&(N-1)
            else:
                i=(r-dpos()-1)&(N-1); n=c-255+TH
                for k in range(n):
                    c2=text[(i+k)&(N-1)]; out.append(c2); text[r]=c2; r=(r+1)&(N-1)
    except EOFErr:
        pass
    return bytes(out)


def main(partial: str, original: str) -> None:
    b = open(partial, "rb").read()
    n = struct.unpack("<I", b[2:6])[0]
    out = decode(b[6:], n)
    hdr_end = out.index(b"\r\n\r\n") + 4
    header = out[:hdr_end].decode("latin-1")
    body_len = int(next(l.split(":")[1] for l in header.splitlines() if l.startswith("Body:")))
    att = out[hdr_end + body_len + 2:]
    orig = open(original, "rb").read()
    first = next((i for i in range(min(len(att), len(orig))) if att[i] != orig[i]), None)
    print(header.strip())
    print(f"compressed bytes in partial: {len(b) - 6}; uncompressed message length {n}")
    if first is None:
        print("attachment matches the original completely")
    else:
        print(f"attachment matches the original for the first {first} of {len(orig)} bytes "
              f"({first / len(orig):.0%}); a match up to about where the compressed data ends "
              f"means no corruption in what was received")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
