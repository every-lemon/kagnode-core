# Changelog

## 1.0.5

- Backport the shared split-orbit loading spinner, reduced-motion/forced-color support and adoption of existing loading surfaces. Preserve compatible 1.0.x update policies; this release does not add the 1.1 search API or update server helpers.

## 1.0.4

- Keep modal input focus when closing mobile navigation and suspend sidebar hover previews behind dialogs.

## 1.0.3

- Restore progressive plan loading after retiring the old bootstrap and ignore hidden targets in contents tracking; track nested scroll containers.

- Correct wrapped navigation icons and linked-profile names in account menus.
- Adapt navigation to available screen space and input capabilities; keep touch drawers and keyboard access. Temporary rail expansion does not move page content.
- Retire duplicate header sign-out controls when the shared account menu is available.

## 1.0.2

- Use GitHub's JSON media type when checking releases. Binary manifest/archive downloads retain their binary request type. This fixes real server checks returning HTTP 415.
- The manager helper requires reviewed installation; automatic updates continue to install UI assets only.

## 1.0.1

Fix drawer controls between application breakpoints, close navigation when dialogs open and keep hidden mobile navigation out of keyboard focus. Adds a browser navigation adapter so hosts do not maintain a second drawer state. Server helpers and the UI API remain unchanged.

## 1.0.0

Initial shared browser UI contract, local Node/Python adapters, pinned offline bundle, native-scrolling rails, manual animated navigation, account appearance connections and signed UI-only patch management. Application deployments and native service qualification are separate from this release.
