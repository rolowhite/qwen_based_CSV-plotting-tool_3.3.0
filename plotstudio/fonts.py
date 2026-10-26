"""The app's IBM Plex fonts (interface, profile dashboard and charts).

The fonts are registered privately for this process only (nothing is installed on the computer):
Windows uses GDI's AddFontResourceEx, Linux uses fontconfig, macOS uses CoreText. If that is not
possible (e.g. a Tk build without anti-aliased fonts), the app falls back to the system's UI font.
Charts get the same fonts through matplotlib's font manager.
"""
from __future__ import annotations

import sys
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
SANS = "IBM Plex Sans"
MONO = "IBM Plex Mono"
# chart fonts in the generated code: Plex when it is installed, then good system fonts
CHART_SANS = [SANS, "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]

_tk_done = None
_mpl_done = False
_win_font_buffers = []
_win_font_handles = []


def font_files():
    return sorted(FONT_DIR.glob("*.ttf")) + sorted(FONT_DIR.glob("*.otf"))


def _tk_files():
    files = font_files()
    if sys.platform not in ("win32", "darwin"):
        # Tk on Linux asks fontconfig for weight "medium" for normal text, which would pick
        # IBM Plex Medium instead of Plex Regular.
        files = [f for f in files if not (f.name.startswith("IBMPlexSans-") and "Medium" in f.name)]
    return files


def register_for_tk() -> bool:
    """Make the bundled fonts available to Tk (call before or right after creating the window)."""
    global _tk_done
    if _tk_done is not None:
        return _tk_done
    files = _tk_files()
    ok = False
    try:
        if sys.platform == "win32":
            import ctypes
            # AddFontResourceExW rejects some valid bundled static TTFs on current
            # Windows builds. Memory registration is still process-private and
            # makes the exact bundled faces available to Tk without installing them.
            gdi = ctypes.WinDLL("gdi32", use_last_error=True)
            add_memory = gdi.AddFontMemResourceEx
            add_memory.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
                                   ctypes.POINTER(ctypes.c_uint32)]
            add_memory.restype = ctypes.c_void_p
            ok = bool(files)
            for path in files:
                try:
                    data = path.read_bytes()
                    buffer = ctypes.create_string_buffer(data)
                    count = ctypes.c_uint32()
                    handle = add_memory(ctypes.cast(buffer, ctypes.c_void_p), len(data), None,
                                        ctypes.byref(count))
                    if handle:
                        _win_font_buffers.append(buffer)
                        _win_font_handles.append(handle)
                    else:
                        ok = False
                except OSError:
                    ok = False
            ok = ok and bool(_win_font_handles)
        elif sys.platform == "darwin":
            ok = _register_macos(files)
        else:
            import ctypes
            import ctypes.util
            name = ctypes.util.find_library("fontconfig")
            if name:
                fc = ctypes.CDLL(name)
                fc.FcConfigGetCurrent.restype = ctypes.c_void_p
                fc.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
                fc.FcConfigAppFontAddFile.restype = ctypes.c_int
                config = fc.FcConfigGetCurrent()
                ok = all(fc.FcConfigAppFontAddFile(config, str(f).encode()) for f in files) and bool(files)
    except Exception:  # noqa: BLE001 - the system font is a fine fallback
        ok = False
    _tk_done = ok
    return ok


def _register_macos(files) -> bool:
    import ctypes
    ct = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreText.framework/CoreText")
    cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long,
                                                           ctypes.c_bool]
    ct.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    ok = bool(files)
    for f in files:
        raw = str(f).encode()
        url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
        if not url:
            ok = False
            continue
        ok = bool(ct.CTFontManagerRegisterFontsForURL(url, 1, None)) and ok   # 1 = this process only
        cf.CFRelease(url)
    return ok


def register_for_matplotlib() -> bool:
    """Let matplotlib draw with Plex (the generated code asks for it by name, with fallbacks)."""
    global _mpl_done
    if _mpl_done:
        return True
    try:
        from matplotlib import font_manager
        for f in font_files():
            font_manager.fontManager.addfont(str(f))
        _mpl_done = True
    except Exception:  # noqa: BLE001
        _mpl_done = False
    return _mpl_done


def resolves(root, name: str, prefix: str = "IBM Plex") -> bool:
    """True when Tk draws the family `name` with a font whose family starts with `prefix`.

    Plex's Medium and SemiBold faces are reached through their own family names
    ("IBM Plex Sans Medm", "IBM Plex Sans SmBld"). Windows lists those names, fontconfig
    resolves them without listing them, and anything unknown falls back to another font.
    """
    from tkinter import font as tkfont
    try:
        actual = tkfont.Font(root=root, family=name, size=10).actual("family")
    except Exception:  # noqa: BLE001
        return False
    return str(actual).lower().startswith(prefix.lower())


def pick(families, *names):
    """The first of `names` that Tk knows (case-insensitive), else None."""
    lower = {f.lower(): f for f in families}
    for n in names:
        if n and n.lower() in lower:
            return lower[n.lower()]
    return None
