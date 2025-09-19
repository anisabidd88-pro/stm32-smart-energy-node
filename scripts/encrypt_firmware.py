#!/usr/bin/env python3
"""Helper: encrypt a firmware file using AES-256-CBC (matching the simulator)."""
import sys, os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

KEY = b"This_is_a_32_byte_key_for_AES_256!!"[:32]

def aes_encrypt_bytes(plain_bytes, key):
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pad_len = 16 - (len(plain_bytes) % 16)
    padded = plain_bytes + bytes([pad_len])*pad_len
    return iv + cipher.encrypt(padded)

def main():
    if len(sys.argv) < 3:
        print("Usage: encrypt_firmware.py input.bin output.enc")
        return
    inp = sys.argv[1]; outp = sys.argv[2]
    with open(inp, "rb") as f:
        data = f.read()
    enc = aes_encrypt_bytes(data, KEY)
    with open(outp, "wb") as f:
        f.write(enc)
    print("Encrypted ->", outp)

if __name__ == '__main__':
    main()
