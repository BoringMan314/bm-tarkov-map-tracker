#!/usr/bin/env python3
from pathlib import Path

data = Path("參考/TarkovMapTracker.exe").read_bytes()
i = data.find(b"parse float 'X':")
print(data[i : i + 300].decode("utf-8", "replace"))
