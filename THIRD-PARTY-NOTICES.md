# Third-Party Notices

GreenUp Label Printer includes or uses third-party software components
listed below.

This document is an informational notice for the dependencies used in
the development/build environment. It is not legal advice and does not
replace the license texts or notices distributed by the respective
authors.

## Application dependencies

  -----------------------------------------------------------------------------------------------------------
  Component                      Version License          Project / license information
  ---------------- --------------------- ---------------- ---------------------------------------------------
  customtkinter                    6.0.0 MIT              https://github.com/TomSchimansky/CustomTkinter

  darkdetect                       0.8.0 MIT              https://github.com/albertosottocornola/darkdetect

  packaging                         26.3 Apache-2.0 OR    https://github.com/pypa/packaging
                                         BSD-2-Clause     

  Pillow                          13.0.0 MIT-CMU          https://python-pillow.org/

  zplkit                           0.3.2 OSL-3.0          https://pypi.org/project/zplkit/
  -----------------------------------------------------------------------------------------------------------

## Build-time and packaging dependencies

The following components are used by the build/packaging environment.
They may be included in the generated application bundle when required
by PyInstaller, but are not direct application features.

  -------------------------------------------------------------------------------------------------------------------------------
  Component                                 Version License            Project / license information
  --------------------------- --------------------- ------------------ ----------------------------------------------------------
  altgraph                                   0.17.5 MIT                https://github.com/ronaldoussoren/altgraph

  pefile                                  2024.8.26 MIT                https://github.com/erocarrera/pefile

  PyInstaller                                6.22.3 GPL-2.0-or-later   https://pyinstaller.org/
                                                    with a special     
                                                    exception          

  pyinstaller-hooks-contrib                  2026.9 Apache-2.0         https://github.com/pyinstaller/pyinstaller-hooks-contrib

  pywin32-ctypes                              0.2.3 BSD-3-Clause       https://github.com/enthought/pywin32-ctypes

  setuptools                                 84.2.1 MIT                https://github.com/pypa/setuptools

  pip                                        26.1.2 MIT                https://github.com/pypa/pip
  -------------------------------------------------------------------------------------------------------------------------------

## Important note about zplkit

`zplkit` 0.3.2 declares the Open Software License 3.0 (OSL-3.0).

OSL-3.0 contains conditions concerning distribution, external
deployment, source-code availability and derivative works. The exact
obligations depend on how the component is used and how the application
is distributed. Including this notice alone does **not** establish
compliance with OSL-3.0.

Before distributing GreenUp Label Printer, review the full OSL-3.0 text
and the `zplkit` package's licensing materials. In particular, determine
whether the way `zplkit` is integrated into and bundled with this
application triggers source-availability or other obligations. If
uncertain, obtain advice from a qualified legal professional or written
clarification from the `zplkit` author.

OSL-3.0 text: https://opensource.org/license/osl-3-0-php

## License notices

The applicable license texts and copyright notices for third-party
components should be retained and made available with the distributed
application where their licenses require it.

For the exact terms, refer to the license files distributed with each
component or the component's official project page. Versions and license
identifiers above reflect the dependency list supplied for this build
and should be rechecked whenever dependencies are upgraded.

## Disclaimer

GreenUp Label Printer is a separate application. Listing a third-party
component here does not imply that its authors endorse, sponsor or are
affiliated with GreenUp Label Printer.
