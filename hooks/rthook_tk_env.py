import os
import sys
from pathlib import Path


base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
tcl_lib = base / "tcl"
tk_lib = base / "tk"

if not tcl_lib.exists():
    legacy_tcl = base / "tcl" / "tcl8.6"
    if legacy_tcl.exists():
        tcl_lib = legacy_tcl

if not tk_lib.exists():
    legacy_tk = base / "tcl" / "tk8.6"
    if legacy_tk.exists():
        tk_lib = legacy_tk

if tcl_lib.exists():
    os.environ["TCL_LIBRARY"] = str(tcl_lib)
if tk_lib.exists():
    os.environ["TK_LIBRARY"] = str(tk_lib)
