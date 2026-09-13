# Debian Package Builder for Notolog Editor

[![GitHub Release](https://img.shields.io/github/v/release/notolog/notolog-debian)](https://github.com/notolog/notolog-debian) [![GitHub License](https://img.shields.io/github/license/notolog/notolog-debian?color=yellow)](https://github.com/notolog/notolog-debian/blob/main/LICENSE) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/notolog/notolog-debian/build.yaml?color=green)](https://github.com/notolog/notolog-debian/actions/workflows/build.yaml)

An isolated build repository for generating `.deb` packages for [Notolog Editor](https://github.com/notolog/notolog-editor) - a Python-powered Markdown editor featuring an integrated AI assistant, on-device LLM support, and optional file encryption.

```
▒█▄░▒█ ▒█▀▀▀▄ ▀▀█▀▀ ▒█▀▀▀▄ ▒█░░░ ▒█▀▀▀▄ ▒█▀▀█░
▒█▒█▒█ ▒█░░▒█ ░▒█░░ ▒█░░▒█ ▒█░░░ ▒█░░▒█ ▒█░░▄▄
▒█░░▀█ ▒█▄▄▄█ ░▒█░░ ▒█▄▄▄█ ▒█▄▄▄ ▒█▄▄▄█ ▒█▄▄▄█
```

This repo contains build scripts, CI/CD workflows, and Debian packaging files used to create and lint compliant `.deb` packages. It does not include application source code.

- 🌐 **Official site**: https://notolog.com
- 📚 **Documentation**: https://notolog.app
- 📦 **Main app repo**: https://github.com/notolog/notolog-editor
- 🛠️ **This builder repo**: https://github.com/notolog/notolog-debian
- 🗃️ **PPA packages**: https://launchpad.net/~notolog/+archive/ubuntu/ppa
- ⚖️ **License**: MIT License

## Installation

### For Users: Install from PPA

The easiest way to install Notolog on Ubuntu:

```bash
# Add the PPA repository
sudo add-apt-repository ppa:notolog/ppa
sudo apt update

# Install Notolog
sudo apt install notolog

# Run
notolog
```

The `amd64` PPA workflow targets Jammy (22.04 LTS), Noble (24.04 LTS), and Resolute
(26.04 LTS). Its default `all` selection builds one application executable and one
shared upstream source archive, then creates the three series-specific source
packages using sortable `~ppa1~ubuntu22.04.1`-style versions. A dry run performs the
complete build and lint checks without signing or uploading; rerun it with dry-run
mode disabled to publish to the configured PPA.

GitHub release builds are native for each architecture: `amd64` is built on Ubuntu
22.04 and targets Ubuntu 22.04 or newer; `arm64` is built on Ubuntu 24.04 and targets
Ubuntu 24.04 or newer. The PPA remains an `amd64`-only binary-repack workflow because
its source upload carries the architecture-specific PyInstaller executable produced
by the Ubuntu 22.04 workflow runner. Launchpad rebuilds the Debian package around
that executable; it does not recompile the application. GitHub's native release
builds are the authoritative standalone package artifacts.

---

### For Developers: Building from Source

> **Note:** The Git repository does not commit generated application binaries or
> third-party runtime packages. Release builds bundle their dependencies and record
> the corresponding licence information in the generated package.

#### System Build Packages

Essential packages required to perform the build:
```bash
sudo apt-get install build-essential zlib1g-dev debhelper devscripts lintian libegl1 libportaudio2
```

#### Python

Python 3.14 with `venv` support is required. `build.sh` creates a builder-owned
virtual environment and installs the pinned PyInstaller and Python build tools;
do not install a separate global PyInstaller for this workflow. Release builds pin
the llama-cpp-python version used by the runtime-backend adapter so rebuilding a
builder tag cannot silently select a different native ABI.

## Building

### Using a Builder Script (preferred)

Clone the matching application release into `src/`, then run the builder from the
repository root:
```bash
git clone --depth 1 --branch v1.2.3 https://github.com/notolog/notolog-editor.git src
./pyinstaller/build.sh
```

#### llama.cpp CPU profiles

The default `auto` profile uses runtime-dispatched llama.cpp CPU backends on
`amd64` and a portable backend on `arm64`, where compiling every backend variant
would make release builds substantially slower. On `amd64`, llama.cpp selects the
best backend supported by the current processor at startup, allowing one package
to retain the ordinary architecture baseline while using F16C, AVX2, and newer
instruction sets where available.

For a smaller generic build without runtime-dispatched backends:

```bash
LLAMA_CPU_PROFILE=portable ./pyinstaller/build.sh
```

The `f16c` profile enables hardware-accelerated half-precision conversions and
can substantially improve llama.cpp CPU inference on compatible `amd64`
processors:

```bash
grep -m1 -w f16c /proc/cpuinfo
LLAMA_CPU_PROFILE=f16c ./pyinstaller/build.sh
```

The build host and every system running an `f16c` build must support F16C. The
script verifies the build host automatically. Prefer `auto` for distributed
packages; use `runtime`, `portable`, or `f16c` only for controlled builds with
specific performance, size, or hardware requirements.

### Release tags

Application and builder tags have different purposes:

* `notolog-editor` uses the upstream application tag, for example `v1.2.3`.
* `notolog-debian` uses the full Debian version, for example
  `v1.2.3-1ubuntu1`.

The builder workflow requires its release tag to equal the version in
`debian/changelog`. The application source must declare the matching upstream
version in `pyproject.toml`; builder tag `v1.2.3-1ubuntu1` therefore packages
application version `1.2.3`. Create the builder tag only after the matching
application release is public and the builder's Launchpad dry run succeeds.

For a release:

1. Run the **Upload to Launchpad PPA** workflow from the release commit with
   `version_override` set to the application tag, `ubuntu_series` set to `all`,
   `ppa_revision` set to `1`, and `dry_run` enabled.
2. Review the generated source-package artifact and confirm that all source,
   lint, bundle, frozen-module, GUI smoke, architecture, glibc, and hardening
   checks pass.
3. Create and push the signed builder tag using the full Debian version.
4. Run the same Launchpad workflow with `dry_run` disabled. Do not start another
   publication run until the queued workflow and Launchpad builds finish.

Each upload version is immutable. If a published package must be rebuilt, increase
the Debian revision or rerun with the next `ppa_revision` instead of moving an
already published tag or reusing an accepted source-package version.

To remove builder-owned generated artifacts:
```bash
./pyinstaller/clean-build.sh
```

### Built Package Installation

The built package can be installed with the command below.
```bash
sudo apt install ../notolog_X.Y.Z-REVISION_ARCH.deb
```

*If the package was built on a local machine, the resulting `.deb` file is typically located in the parent directory (`..`) relative to where the `debian/` directory resides.*

### PyInstaller spec file

`pyinstaller/notolog-onefile.spec` is the authoritative standalone-binary definition.
Use `./pyinstaller/build.sh` so the native bootloader, llama.cpp library, dependency
audit, license report, and Debian package are produced consistently.

## PyInstaller Init Script

The init script `pyinstaller/runtime_hooks/init.py` configures the app on first run based on user settings and package type. It verifies the current package type and adjusts settings accordingly.

### Possible Issues

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
reuse annotate --copyright="2024-2026 Author Name" \
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

Inspect `.deb` contents:
```bash
dpkg-deb -c notolog_*.deb
```

PyInstaller one-file packages store shared objects inside the executable archive,
so they do not appear as separate files in `dpkg-deb -c` output.

If using a `--onefile` PyInstaller build, run the app once to trigger runtime extraction. Then inspect with:
```bash
ps aux | grep notolog
lsof -p $(pgrep notolog) | grep _MEI
# The default extraction directory is a private, per-process _MEI directory
# under the user's secure temporary directory.
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
RUNTIME_DIR=$(lsof -p "$(pgrep -n notolog)" | awk '/_MEI/ {print $9; exit}')
find "$RUNTIME_DIR" -path '*llama_cpp*' -name 'libllama.so' -exec ldd {} \;
```

### License Check

To verify bundled binaries for license metadata, use licensecheck:
```bash
licensecheck --shortname-scheme new --recursive "$RUNTIME_DIR"
```

`RUNTIME_DIR` is discovered from the running process because PyInstaller creates a
private randomized extraction directory for every launch.

The `--shortname-scheme new` flag ensures SPDX-style identifiers (e.g. mit, lgpl-2.1+, etc.).

This is especially useful for auditing libraries bundled in `--onefile` PyInstaller builds.

## CI/CD workflows

The build process is automated using GitHub Actions, and the resulting artifact is uploaded after the workflow completes.

Refer to `.github/workflows/build.yaml` for details and step-by-step instructions.

## Contributing

See [CONTRIBUTING.md](https://github.com/notolog/notolog-debian/blob/main/CONTRIBUTING.md) for guidelines.

## Licensing

This repository contains only build scripts and CI workflows.
It does not include or redistribute any third-party software.

All third-party dependencies are pulled by the main application during build and bundled into the final `.deb` as part of the PyInstaller runtime. Licensing for each is tracked and included in the package metadata.

🦙 The CPU-only llama-cpp backend is built from source and dynamically links to:

- `libgomp` and `libstdc++`: covered under the GPL with the [GCC Runtime Library Exception](https://www.gnu.org/licenses/gcc-exception-3.1.html), which permits linking from non-GPL software.
- MIT-licensed internal `libggml` backends (`libggml.so`, `libggml-base.so`, and the selected `libggml-cpu-*.so` variant).
