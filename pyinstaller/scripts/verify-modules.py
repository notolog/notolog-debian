# SPDX-FileCopyrightText: 2025-2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

"""
Notolog Editor - Debian Package Builder
Build scripts and packaging for the Notolog Editor Debian release.

File Details:
- Purpose: Verify that every bundled AI backend is importable before freezing.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app

Author: Vadim Bakhrenkov
Copyright: 2025-2026 Vadim Bakhrenkov
License: MIT License

For detailed instructions and project information, please see the repository's README.md.
"""

import ctypes
import os

from pathlib import Path

import llama_cpp
from notolog.modules.modules import Modules
from llama_cpp import llama_backend_free, llama_backend_init

EXPECTED_AI_MODULES = {"llama_cpp", "ondevice_llm", "openai_api", "text_to_speech"}


def load_runtime_cpu_backend():
    library_dir = Path(llama_cpp.__file__).resolve().parent / "lib"
    if not any(library_dir.glob("libggml-cpu-*.so")):
        return

    ggml_path = library_dir / "libggml.so.0"
    if not ggml_path.is_file():
        raise RuntimeError("llama.cpp runtime is missing libggml.so.0")

    library = ctypes.CDLL(str(ggml_path))
    library.ggml_backend_load_all_from_path.argtypes = [ctypes.c_char_p]
    library.ggml_backend_load_all_from_path.restype = None
    library.ggml_backend_dev_count.argtypes = []
    library.ggml_backend_dev_count.restype = ctypes.c_size_t
    library.ggml_backend_load_all_from_path(os.fsencode(library_dir))
    if library.ggml_backend_dev_count() == 0:
        raise RuntimeError("No llama.cpp CPU backend could be loaded")


def main() -> int:
    loaded_modules = set(Modules().modules)
    missing_modules = EXPECTED_AI_MODULES - loaded_modules
    if missing_modules:
        names = ", ".join(sorted(missing_modules))
        print(f"AI module discovery failed: {names}")
        return 1

    import sounddevice

    sounddevice.get_portaudio_version()
    llama_backend_init()
    load_runtime_cpu_backend()
    llama_backend_free()

    print("AI module imports and llama.cpp CPU backend initialization OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
