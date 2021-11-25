import time
from litex import RemoteClient

wb = RemoteClient()


def print_regs(matching="_", count=1):
    for i in range(count):
        time.sleep(.01)
        for r in wb.regs.__dict__:
            v = getattr(wb.regs, r).read()
            if (matching in r):
                print(f"{r} = {v} ({hex(v)})")

def read_mem(start=0x03000000, len=64):
    for addr in range(start, start+len, 4):
        wb.read(addr)

def print_mem(start=0x03000000, len=64):
    for base in range(start, start+len, 16):
        print(f"{hex(base)}: ", end='')
        for addr in range(base, base+16, 4):
            #time.sleep(.01)
            print(f"{hex(wb.read(addr))} ", end='')
        print("")

def setup():
    wb.open()

