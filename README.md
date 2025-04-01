<!-- {"notolog.app": {"created": "2025-04-01 00:00:00.000000", "updated": "2025-04-01 00:00:00.000000"}} -->
# Debian Package Builder for Notolog Editor

An isolated build repository for generating `.deb` packages for [Notolog Editor](https://github.com/notolog/notolog-editor) — an open-source Markdown editor built with Python and PySide6, featuring an integrated AI assistant.

```
▒█▄░▒█ ▒█▀▀▀▄ ▀▀█▀▀ ▒█▀▀▀▄ ▒█░░░ ▒█▀▀▀▄ ▒█▀▀█░
▒█▒█▒█ ▒█░░▒█ ░▒█░░ ▒█░░▒█ ▒█░░░ ▒█░░▒█ ▒█░░▄▄
▒█░░▀█ ▒█▄▄▄█ ░▒█░░ ▒█▄▄▄█ ▒█▄▄▄ ▒█▄▄▄█ ▒█▄▄▄█
```

This repo contains build scripts, CI/CD workflows, and Debian packaging files used to create and lint compliant `.deb` packages. It does not include application source code.

- 📦 **Main app repo**: https://github.com/notolog/notolog-editor
- 🛠️ **This builder repo**: https://github.com/notolog/notolog-debian
- ⚖️ **License**: MIT License

## Installation

> **Note:** This repository does not contain any third-party software.
> All third-party dependencies are bundled and attributed within the application package during the build process.

### System Build Packages

Essential packages required to perform the build:
```bash
sudo apt-get install build-essential debhelper lintian
```

#### Python Dependencies

Essential Python packages:
```bash
pip install pyinstaller
```

#### Optional Packages

Optional system packages (install only if needed by your environment):
```bash
dh-autoreconf dh-exec g++ g++-12 libc6-dev libstdc++-12-dev libtool linux-libc-dev
```

## Info

### Binary Package Date

The date of the generated .deb file is derived from the changelog.

### Cache and Side Effects

Remove any installed version of the package (e.g., `notolog` via pip) to avoid conflicts between the source and installed resources.

#### Conflict between local source and installed package

If both the local source `appname` (notolog/) and a pip-installed package `appname` (notolog) exist, PyInstaller may bundle the wrong version depending on the `PYTHONPATH` and Python's module resolution order.

* Local Source Directory: If `appname` is a local directory in your project root, PyInstaller will use the local source files, provided they are imported directly in the code.
* Installed Package: If your environment resolves the `appname` module from site-packages, PyInstaller will bundle the installed version from `pip`.

## Building

### Using a Builder Script (preferred)

Navigate to the `pyinstaller/` directory and run one of the following commands:
```bash
cd pyinstaller
sudo ./build.sh
# or
bash build.sh
```

To clean up cached data and perform linting, use the `post-build.sh` script located in the `pyinstaller/` directory:
```bash
bash post-build.sh
```

### Built Package Installation

The built package can be installed with the command below.
```bash
sudo dpkg -i notolog_X.Y.Z_amd64.deb
```

*If the package was built on a local machine, the resulting `.deb` file is typically located in the parent directory (`..`) relative to where the `debian/` directory resides.*

### Using a .spec File (manual build without script)

Clean up .pyc files before building:
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
```

Ensure a clean PyInstaller environment:
```bash
pyinstaller --clean notolog-onefile.spec
```
Run the build with one of the following options:
```bash
pyinstaller notolog-onefile.spec
```

Set the `app_root` variable if building from within the `pyinstaller/` directory. Leave it unset if building from the project root.

### CLI Build Examples

One-file build:
```bash
pyinstaller --onefile --noconfirm --name=notolog \
  --collect-all=notolog notolog/app.py \
  --add-data="notolog:notolog" \
  --add-data="docs/*:docs" \
  --add-data="CHANGELOG.md:." \
  --add-data="CODE_OF_CONDUCT.md:." \
  --add-data="LICENSE:." \
  --add-data="README.md:." \
  --add-data="ThirdPartyNotices.md:." \
  --exclude-module __pycache__ \
  --exclude-module "*.pyc" \
  --exclude-module "*.pyo" \
  --add-data="../venv/notolog/lib/python3.11/site-packages/emoji:emoji"
```

One-dir build:
(Same as above, just replace `--onefile` with `--onedir`.)

## PyInstaller Init Script

The init script `pyinstaller/runtime_hooks/init.py` configures the app on first run based on user settings and package type. It verifies the current package type and adjusts settings accordingly.

### Possible Issues

#### NumPy Import Error

> Error importing numpy: you should not try to import numpy from its source directory

The issue may be caused by incompatible NumPy versions. Version 1.26.4 works fine, while versions 2.1.0 and later (e.g., 2.2.2) may result in errors. Check the version compatibility.

#### Qt Platform Plugin (xcb) Error

If you see:
```bash
qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed to load the Qt xcb platform plugin.
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

Available platform plugins are: linuxfb, minimalegl, xcb, minimal, vkkhrdisplay, wayland, vnc, offscreen, wayland-egl, eglfs.

Aborted (core dumped)
```

Install the required package:
```bash
sudo apt-get install libxcb-cursor0
```

## Linter

### REUSE-compliance Tools:

* REUSE https://reuse.software/faq/
    * Bulk-license whole directories https://reuse.software/faq/#bulk-license
    * Add copyright and licensing information to an uncommentable file https://reuse.software/faq/#uncommentable-file
* SPDX Licenses https://spdx.org/licenses/
* See `debian/copyright` for a full SPDX-compatible license inventory.

Install REUSE
```bash
pip install reuse
```

Fetch missing licenses
```bash
# Download all SPDX-referenced licenses
reuse download --all
# Or download a specific license and place it in the LICENSES/ directory
reuse download PSF-2.0
```

Run REUSE linting
```bash
reuse lint
```

Annotate specific files
```bash
reuse annotate --copyright="2024-2025 Author Name" \
  --license="MIT" --skip-unrecognised \
  debian/README.md debian/changelog debian/control
```

### Check .deb File

Lint the built `.deb` package:
```bash
sudo apt-get install -y lintian
lintian notolog.deb
```

For detailed output and to help debug any issues, use the `--info` flag:
```bash
lintian -i notolog.deb
# Or, for even more verbose output:
lintian -iIv notolog.deb
```

Make sure to follow the guidelines in `debian/copyright`:
```
# Please also look if there are files or directories which have a
# different copyright/license attached and list them here.
# Please avoid picking licenses with terms that are more restrictive than the
# packaged work, as it may make Debian's contributions unacceptable upstream.
#
# If you need, there are some extra license texts available in two places:
#   /usr/share/debhelper/dh_make/licenses/
#   /usr/share/common-licenses/
```

### Check PIE

PIE (Position Independent Executable) hardening ensures that the binary can be loaded at a random memory address each time it runs.

This enhances security by enabling ASLR (Address Space Layout Randomization), which protects against memory corruption attacks like buffer overflows.

For `.deb` packages, this is a Debian security best practice and is checked by tools like `lintian`.

#### Verify PIE status

After building, run:
```bash
hardening-check pyinstaller/dist/notolog
# Or, if the app is already installed:
hardening-check /usr/bin/notolog
```

You want to see:
```text
Position Independent Executable: yes
```

Or, to check manually with readelf:
```bash
readelf -h /usr/bin/notolog | grep 'Type'
```

Expected output:
```text
Type: DYN (Position-Independent Executable)
```

### Validate .desktop File

Run this to validate:
```bash
desktop-file-validate /usr/share/applications/notolog.desktop
```

### Validate man Page

```bash
dpkg-deb -c notolog_*.deb | grep 'man/man1'
```

The output should be:
```text
./usr/share/man/man1/notolog.1.gz
```

Then check the `man` entry:
```bash
man notolog
```

## Licensing & Dependency Inspection

Use these steps to verify what's bundled into the PyInstaller binary - important for compliance, reproducibility, and Debian policy alignment.

### Confirm What's Inside

Inspect .deb contents:
```bash
dpkg -c notolog.deb | grep '\.so'
```

Find bundled shared objects in PyInstaller output:
```bash
find pyinstaller/dist/ -name "*.so*"
```

If using a `--onefile` PyInstaller build, run the app once to trigger runtime extraction. Then inspect with:
```bash
ps aux | grep notolog
lsof -p $(pgrep notolog) | grep _MEI
# Or manually inspect the runtime directory:
find /usr/lib/notolog/runtime -type f
```

Optional: Use `strace` if you need syscall-level info:
```bash
strace -f -e trace=openat /usr/bin/notolog
```

Note: `strace` is a syscall tracer. It works by launching (or attaching to) the process and intercepting all syscalls (like `openat`, `read`, etc.).
This means it will run the app while tracing - that's expected behavior.

See linked shared libraries:
```bash
ldd /usr/bin/notolog
```

Check which Debian package provides a library:
```bash
dpkg -S libexpat.so.1
# or
apt show libexpat1
# and
cat /usr/share/doc/libexpat1/copyright
```

To inspect the contents of a PyInstaller executable (ensure the virtual environment is activated):
```bash
pyi-archive_viewer pyinstaller/dist/notolog
```

Inside the viewer shell:
```shell
> ls
> extract libexpat.so.1
```

### Check llama-cpp Runtime Linking

To confirm `libllama.so` and its dependencies are dynamically linked and runtime-bundled:
```bash
ldd /usr/lib/notolog/runtime/_MEI*/llama_cpp/lib/libllama.so
```

### License Check

To verify bundled binaries for license metadata, use licensecheck:
```bash
licensecheck --shortname-scheme new --recursive /usr/lib/notolog/runtime/_MEIXXXX/
```

Replace `_MEIXXXX` with the actual unpacked PyInstaller runtime path.

The `--shortname-scheme new` flag ensures SPDX-style identifiers (e.g. mit, lgpl-2.1+, etc.).

This is especially useful for auditing libraries bundled in `--onefile` PyInstaller builds.

### Post-Build Inspection

Optional but Recommended. Add this to CI or locally:
```bash
pyi-archive_viewer pyinstaller/dist/notolog | tee archive-contents.txt
strings pyinstaller/dist/notolog | grep -iE 'key|token|user|secret|home|/Users|/home|__pycache__'
```

This confirms no credentials, user paths, or environment variables leaked into the binary (e.g., from `.env`, dev configs, etc.).

---

For easier debugging and inspection, consider building with `--onedir`.

Note: onedir is not recommended for final Debian packaging, as it unpacks dozens of files and complicates reproducibility. Stick to `--onefile` for cleaner shipping.

## Metadata

The upstream metadata file should be located at `debian/upstream/metadata`. If using an example (`metadata.ex`), make sure to rename it to just `metadata`.

* See: https://wiki.debian.org/UpstreamMetadata for more information.

Example:
```yaml
# User support or community link
Support: https://github.com/notolog/notolog-editor/discussions
```

## CI/CD workflows

The build process is automated using GitHub Actions, and the resulting artifact is uploaded after the workflow completes.

Refer to `.github/workflows/build.yaml` for details and step-by-step instructions.

## Licensing

This repository contains only build scripts and CI workflows.
It does not include or redistribute any third-party software.

All third-party dependencies are pulled by the main application during build and bundled into the final `.deb` as part of the PyInstaller runtime. Licensing for each is tracked and included in the package metadata.

🦙 The CPU-only llama-cpp backend is built from source and dynamically links to:

- `libgomp` and `libstdc++`: covered under the GPL with the [GCC Runtime Library Exception](https://www.gnu.org/licenses/gcc-exception-3.1.html), which permits linking from non-GPL software.
- MIT-licensed internal `libggml` backends (`libggml.so`, `libggml-base.so`, `libggml-cpu.so`).

---
_This README.md file has been carefully crafted and edited using the Notolog Editor itself._
