# Changelog

## 1.2.4

- Preserve deliberate keyboard browsing when an overflowing contents list itself has visible focus and headings load or resize. Continue centering focused links and resume active-heading tracking after focus leaves. Add Chromium/WebKit container/anchor/resize regressions with normal and reduced motion.

## 1.2.3

- Keep sidebar group accessibility states synchronized when collapsing the sidebar cancels submenu animation. Repeated collapse/expand cycles retain closed, unfocusable children and announce groups correctly in Chromium and WebKit, with normal and reduced motion.

## 1.2.2

- Invalidate quick-search selection and full-search destinations immediately when typing a new query, before debounce. Keep IME Escape inside composition and bind each request deadline to its own abort controller. Add Chromium/WebKit regressions for stale navigation, composition, request cancellation and late responses.

## 1.2.1

- Recover abandoned update journals using the operation lock, offline signed-cache verification and ownership-marked scratch cleanup. Preserve activation, policies, live operations and unrelated files. Reviewed manager installation is required; UI patches cannot replace server helpers.

## 1.2.0

- Require an explicit application declaration or baseline when creating bindings; remove the silent 1.0.x default.
- Add root-reviewed CLI baseline adoption with signed current/target caches, conflict checks, source verification and recoverable UI rollback. Preserve paused update policies and newer compatible patches. Ordinary web update operations remain patch-only.
- Cache an unchanged current UI on manual apply without losing its prior rollback pointer. Report rollback status accurately. Manager installation requires explicit review; automatic UI patches cannot install these helpers or change existing baseline lines.

## 1.1.5

- Return structured validation errors for non-object JSON sent to the private manager socket, retaining a working status interface after malformed requests.
- Record the actual reviewed adapter version when refreshing pinned fallbacks, while preserving the installation’s automatic-update policy. Server helper installation remains separate from UI-only automatic patches.

## 1.1.4

- Add the shared KagNode split-orbit spinner: a stationary canonical mark with an orbiting separated accent, reduced-motion and forced-color support. Adopt existing application loading screens without replacing their status or recovery controls.

## 1.1.3

- Keep background update error recording inside the operation lock. Busy manual updates no longer trigger unlocked state writes or false failure status. Installing the manager helper still requires administrator review; automatic patches only activate UI assets.

## 1.1.2

- Start Up-arrow navigation at the last quick-search result when no result is selected. Server helper behavior is unchanged.

## 1.1.1

- Preserve JSON and plain-text responses containing HTML-like text in the Node adapter. Server adapter updates remain reviewed separately from automatic UI patches.

## 1.1.0

- Add shared quick search with authorized host results, cancellable requests, keyboard navigation and responsive modal layout.
- Avoid initial content slides beneath navigation and ignore height-only sidebar state resets.
- Retain the 1.0.4 modal focus repairs. Applications explicitly review this minor baseline upgrade.

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
