"""
Notolog Editor - Application Runtime Hook
Initializes and configures the application based on user settings and package type.

File Details:
- Purpose: This file is bundled into the final application build.
- Functionality: Verifies the current package type and updates configuration settings accordingly.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app
Documentation: https://notolog.app
PyPI: https://pypi.org/project/notolog

Author: Vadim Bakhrenkov
Copyright: 2025-2026 Vadim Bakhrenkov
License: MIT License

SPDX-FileCopyrightText: 2025-2026 Vadim Bakhrenkov
SPDX-License-Identifier: MIT

For detailed instructions and project information, please refer to the repository's README.md.
"""

import sys
import runpy
from pathlib import Path

import ctypes
import logging
import os

# 'bin' denotes the PyInstaller-built binary package
app_package = "bin"
_ggml_library = None


def main():
    from notolog.app_config import AppConfig
    from notolog.app_package import AppPackage

    # Initialize application logger
    logger = logging.getLogger("init")

    # Log debug information if debugging is enabled
    logger.info("Startup hook executed before main application.")

    # Check if the package has already been set
    if not AppPackage().validate_config(AppPackage().get_config()):
        try:
            # Initialize or update configuration settings for the new package type
            AppConfig().setup_package(app_package)
        except Exception as e:
            logger.error(f"Error occurred during init process: {e}")

        # Log the package type update if debugging is enabled
        logger.debug(f"App package set to '{app_package}'")


def load_llama_cpu_backend():
    """Load the best runtime-dispatched llama.cpp CPU backend, when bundled."""
    import llama_cpp
    from llama_cpp import llama_backend_init

    library_dir = Path(llama_cpp.__file__).resolve().parent / "lib"
    if not any(library_dir.glob("libggml-cpu-*.so")):
        return

    ggml_path = library_dir / "libggml.so.0"
    if not ggml_path.is_file():
        raise RuntimeError("Bundled llama.cpp runtime is missing libggml.so.0")

    llama_backend_init()
    global _ggml_library
    _ggml_library = ctypes.CDLL(str(ggml_path))
    _ggml_library.ggml_backend_load_all_from_path.argtypes = [ctypes.c_char_p]
    _ggml_library.ggml_backend_load_all_from_path.restype = None
    _ggml_library.ggml_backend_dev_count.argtypes = []
    _ggml_library.ggml_backend_dev_count.restype = ctypes.c_size_t
    _ggml_library.ggml_backend_load_all_from_path(os.fsencode(library_dir))
    if _ggml_library.ggml_backend_dev_count() == 0:
        raise RuntimeError("No bundled llama.cpp CPU backend could be loaded")


def verify_modules():
    """Verify optional modules from inside the frozen application."""
    from notolog.modules.modules import Modules

    expected_modules = {
        "default",
        "llama_cpp",
        "ondevice_llm",
        "openai_api",
        "text_to_speech",
    }
    available_modules = set(Modules().modules)
    missing_modules = sorted(expected_modules - available_modules)
    if missing_modules:
        raise RuntimeError(
            f"Frozen module verification failed: {', '.join(missing_modules)}"
        )

    import sounddevice

    sounddevice.get_portaudio_version()

    from llama_cpp import llama_backend_free, llama_backend_init

    llama_backend_init()
    llama_backend_free()

    print(f"Frozen modules verified: {', '.join(sorted(available_modules))}")


if __name__ == "__main__":
    # The speech worker runs before application settings and AI backends initialize.
    if sys.argv[1:] == ["--tts-worker"]:
        runpy.run_path(
            str(Path(sys._MEIPASS) / "notolog/modules/text_to_speech/native_worker.py"),
            run_name="__main__",
        )
        raise SystemExit(0)
    main()
    load_llama_cpu_backend()
    if os.environ.get("NOTOLOG_VERIFY_FROZEN_MODULES") == "1":
        verify_modules()
        raise SystemExit(0)
