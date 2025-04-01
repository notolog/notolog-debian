"""
Notolog Editor - Application Runtime Hook
Initializes and configures the application based on user settings and package type.

File Details:
- Purpose: This file is bundled into the final application build.
- Functionality: Verifies the current package type and updates configuration settings accordingly.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app
PyPI: https://pypi.org/project/notolog

Author: Vadim Bakhrenkov
Copyright: 2025 Vadim Bakhrenkov
License: MIT License

SPDX-FileCopyrightText: 2025 Vadim Bakhrenkov
SPDX-License-Identifier: MIT

For detailed instructions and project information, please refer to the repository's README.md.
"""

from notolog.app_config import AppConfig
from notolog.app_package import AppPackage

import logging

# 'bin' denotes the PyInstaller-built binary package
app_package = 'bin'


def main():
    # Initialize application logger
    logger = logging.getLogger('init')

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


if __name__ == '__main__':
    main()
