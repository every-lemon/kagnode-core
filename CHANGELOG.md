# Changelog

## 1.0.2

- Use GitHub's JSON media type when checking releases. Binary manifest/archive downloads retain their binary request type. This fixes real server checks returning HTTP 415.
- The manager helper requires reviewed installation; automatic updates continue to install UI assets only.

## 1.0.1

Fix drawer controls between application breakpoints, close navigation when dialogs open and keep hidden mobile navigation out of keyboard focus. Adds a browser navigation adapter so hosts do not maintain a second drawer state. Server helpers and the UI API remain unchanged.

## 1.0.0

Initial shared browser UI contract, local Node/Python adapters, pinned offline bundle, native-scrolling rails, manual animated navigation, account appearance connections and signed UI-only patch management. Application deployments and native service qualification are separate from this release.
