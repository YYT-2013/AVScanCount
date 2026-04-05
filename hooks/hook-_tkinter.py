import os
import sys


datas = []


def _collect_dir(src_root: str, dest_prefix: str) -> None:
    for root, _, files in os.walk(src_root):
        rel = os.path.relpath(root, src_root)
        if rel == ".":
            dest_dir = dest_prefix
        else:
            dest_dir = f"{dest_prefix}/{rel.replace(os.sep, '/')}"
        for name in files:
            datas.append((os.path.join(root, name), dest_dir))


base = sys.base_prefix
tcl_root = os.path.join(base, "tcl")
tcl86 = os.path.join(tcl_root, "tcl8.6")
tk86 = os.path.join(tcl_root, "tk8.6")

if os.path.isdir(tcl86):
    _collect_dir(tcl86, "tcl")
if os.path.isdir(tk86):
    _collect_dir(tk86, "tk")
