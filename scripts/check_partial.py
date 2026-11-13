#!/usr/bin/env python3
"""Check a Winlink Express partial (Partials/<MID>.bin) against the payload that was sent.

A partial holds the B2F compressed stream received so far: CRC16 (2 bytes), uncompressed
length (4 bytes, little-endian), then LZHUF data (Okumura, N=2048, F=60, THRESHOLD=2).
This decodes it and reports how far the attachment matches the original file, which
tells a corrupted transfer from one that simply stopped. It also re-compresses the
original message and lists the exact compressed bytes that differ.

    python3 scripts/check_partial.py <MID>.bin payloads/Text_50KB[/<file>.txt]
"""
import os
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


NIL = N
p_len = bytes([3]*1 + [4]*3 + [5]*8 + [6]*12 + [7]*24 + [8]*16)
p_code = bytes([0x00,0x20,0x30,0x40,0x50,0x58,0x60,0x68,0x70,0x78,0x80,0x88,0x90,0x94,0x98,0x9C,0xA0,0xA4,0xA8,0xAC,0xB0,0xB4,0xB8,0xBC,
 0xC0,0xC2,0xC4,0xC6,0xC8,0xCA,0xCC,0xCE,0xD0,0xD2,0xD4,0xD6,0xD8,0xDA,0xDC,0xDE,0xE0,0xE2,0xE4,0xE6,0xE8,0xEA,0xEC,0xEE,
 0xF0,0xF1,0xF2,0xF3,0xF4,0xF5,0xF6,0xF7,0xF8,0xF9,0xFA,0xFB,0xFC,0xFD,0xFE,0xFF])
def encode(data):
    text=bytearray(N+F-1); lson=[0]*(N+1); rson=[0]*(N+257); dad=[0]*(N+1)
    st={'mpos':0,'mlen':0}
    def init_tree():
        for i in range(N+1,N+257): rson[i]=NIL
        for i in range(N): dad[i]=NIL
    def insert(r):
        cmp=1; key=r; p=N+1+text[key]; rson[r]=lson[r]=NIL; st['mlen']=0
        while True:
            if cmp>=0:
                if rson[p]!=NIL: p=rson[p]
                else: rson[p]=r; dad[r]=p; return
            else:
                if lson[p]!=NIL: p=lson[p]
                else: lson[p]=r; dad[r]=p; return
            i=1
            while i<F:
                cmp=text[key+i]-text[p+i]
                if cmp!=0: break
                i+=1
            if i>TH:
                if i>st['mlen']:
                    st['mpos']=((r-p)&(N-1))-1
                    st['mlen']=i
                    if i>=F: break
                if i==st['mlen']:
                    c=((r-p)&(N-1))-1
                    if c<st['mpos']: st['mpos']=c
        dad[r]=dad[p]; lson[r]=lson[p]; rson[r]=rson[p]
        dad[lson[p]]=r; dad[rson[p]]=r
        if rson[dad[p]]==p: rson[dad[p]]=r
        else: lson[dad[p]]=r
        dad[p]=NIL
    def delete(p):
        if dad[p]==NIL: return
        if rson[p]==NIL: q=lson[p]
        elif lson[p]==NIL: q=rson[p]
        else:
            q=lson[p]
            if rson[q]!=NIL:
                while rson[q]!=NIL: q=rson[q]
                rson[dad[q]]=lson[q]; dad[lson[q]]=dad[q]
                lson[q]=lson[p]; dad[lson[p]]=q
            rson[q]=rson[p]; dad[rson[p]]=q
        dad[q]=dad[p]
        if rson[dad[p]]==p: rson[dad[p]]=q
        else: lson[dad[p]]=q
        dad[p]=NIL
    freq=[0]*(T+1); prnt=[0]*(T+N_CHAR); son=[0]*T
    for i in range(N_CHAR): freq[i]=1; son[i]=i+T; prnt[i+T]=i
    i,j=0,N_CHAR
    while j<=R:
        freq[j]=freq[i]+freq[i+1]; son[j]=i; prnt[i]=prnt[i+1]=j; i+=2; j+=1
    freq[T]=0xffff; prnt[R]=0
    out=bytearray(); pb={'buf':0,'len':0}
    def putcode(l,c):
        pb['buf']|=c>>pb['len']; pb['len']+=l
        if pb['len']>=8:
            out.append((pb['buf']>>8)&0xff); pb['len']-=8
            if pb['len']>=8:
                out.append(pb['buf']&0xff); pb['len']-=8
                pb['buf']=(c<<(l-pb['len']))&0xffff
            else:
                pb['buf']=(pb['buf']<<8)&0xffff
    def reconst():
        j=0
        for i in range(T):
            if son[i]>=T: freq[j]=(freq[i]+1)//2; son[j]=son[i]; j+=1
        i=0; j=N_CHAR
        while j<T:
            f=freq[j]=freq[i]+freq[i+1]
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
    def enc_char(c):
        i=0; j=0; k=prnt[c+T]
        while True:
            i>>=1
            if k&1: i+=0x8000
            j+=1; k=prnt[k]
            if k==R: break
        putcode(j,i); update(c)
    def enc_pos(c):
        i=c>>6; putcode(p_len[i], p_code[i]<<8); putcode(6, (c&0x3f)<<10)
    init_tree(); s=0; r=N-F
    for i in range(s,r): text[i]=0x20
    ln=0
    while ln<F and ln<len(data): text[r+ln]=data[ln]; ln+=1
    ip=ln
    for i in range(1,F+1): insert(r-i)
    insert(r)
    while True:
        if st['mlen']>ln: st['mlen']=ln
        if st['mlen']<=TH:
            st['mlen']=1; enc_char(text[r])
        else:
            enc_char(255-TH+st['mlen']); enc_pos(st['mpos'])
        last=st['mlen']; i=0
        while i<last and ip<len(data):
            c=data[ip]; ip+=1
            delete(s); text[s]=c
            if s<F-1: text[s+N]=c
            s=(s+1)&(N-1); r=(r+1)&(N-1); insert(r); i+=1
        while i<last:
            i+=1; delete(s); s=(s+1)&(N-1); r=(r+1)&(N-1); ln-=1
            if ln: insert(r)
        if ln<=0: break
    if pb['len']: out.append((pb['buf']>>8)&0xff)
    return bytes(out)


def main(partial: str, original: str) -> None:
    b = open(partial, "rb").read()
    n = struct.unpack("<I", b[2:6])[0]
    got = b[6:]
    out = decode(got, n)
    hdr_end = out.index(b"\r\n\r\n") + 4
    header = out[:hdr_end].decode("latin-1")
    body_len = int(next(l.split(":")[1] for l in header.splitlines() if l.startswith("Body:")))
    att0 = hdr_end + body_len + 2
    if os.path.isdir(original):    # a payload folder: use the file named in the header
        name = next(l.split()[-1] for l in header.splitlines() if l.startswith("File:"))
        original = os.path.join(original, name)
    orig = open(original, "rb").read()
    att = out[att0:]
    first = next((i for i in range(min(len(att), len(orig))) if att[i] != orig[i]), None)
    print(header.strip())
    print(f"compressed bytes in partial: {len(got)}; uncompressed message length {n}")
    print("decoded attachment matches the original " +
          ("completely" if first is None else f"for the first {first} of {len(orig)} bytes"))
    # Re-compress what was sent (header and body as received, attachment from the
    # original file) and compare the compressed streams byte for byte. The few bytes
    # after the attachment aren't known, so the last 8 compressed bytes are ignored.
    sent = encode(out[:att0] + orig + out[att0 + len(orig):n].ljust(n - att0 - len(orig), b"\0"))
    upto = min(len(got), len(sent) - 8)
    diffs = [i for i in range(upto) if sent[i] != got[i]]
    print(f"compressed stream re-built from the original: {len(sent)} bytes; "
          f"compared {upto} received bytes: {len(diffs)} differ")
    for i in diffs[:20]:
        e, g = sent[i], got[i]
        print(f"  offset {i} (B2F stream {i + 6}): sent {e:08b} got {g:08b}  xor {e ^ g:08b}")
    if not diffs:
        print("no corruption in what was received; the transfer stopped early" if len(got) < len(sent) - 8
              else "no corruption")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
