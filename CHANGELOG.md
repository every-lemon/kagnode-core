## 5.0.11

- Bind custom fields and popovers to the active Core appearance, including legacy hosts.
- Correct checkbox geometry and indeterminate state; add opt-in accessible animated setting switches.
- Animate forward/back folder navigation and repair collapsed quick-search geometry.

# 5.0.10

- Expose canonical server-rendered login, sidebar and account templates in the Rust adapter.
- Add independent Stable/Beta and Auto/Manual Core UI policy, signed beta validation and version ordering without downgrades.
- Keep baseline and backend adapter changes under explicit application review.

# Changelog

## 5.0.9

- Add a framework-independent Rust server adapter with checksum-checked offline assets, protected compatible cache lookup and the existing authenticated Unix HTTP manager transport.
- Publish readable Rust adapter source archives. Keep backend adapter adoption explicit; automatic patches still change UI assets only.
- Exclude native build targets and dependency caches from corresponding-source packages and vendoring.

## 5.0.8

- Cancel both preliminary CSRF and component-status reads during real reload/navigation; prevent stale results from replacing current-session state.
- Keep background status checks noninteractive and resume read-only refreshes after restored pages.
- Give administrative actions independent loading handles and prevent interrupted check/apply or reauthentication continuations from replaying.

## 5.0.7

- Separate scroll runtime state from preference actions so ordinary clicks never persist a scroll setting.
- Abort and defer background update-summary reads during navigation, hidden pages and loading; resume intercepted views and restored pages safely.
- Preserve visible-notice dismissal across unrelated background loading operations.

## 5.0.6

- Add keyboard-operated sliding segments, native mobile sheets and composable contextual loading operations.
- Correct circular account avatars and suppress redundant sidebar rails while preserving the native-scrolling preference.
- Respect deliberate contents-list browsing during layout and fragment changes.
- Add optional signed UI update summaries, local administrator policy and authenticated per-account dismissal adapters. The new backend helper requires explicit review and installation; automatic updates still replace UI assets only.

## 5.0.5

- Add progressive identity/password login without changing native submission, autofill or existing MFA continuations.
- Support same-tab KagNode authorization and clean, readiness-gated callback resumption alongside existing device-code login.
- Preserve pending browser attempts during deliberate issuer navigation, with trusted-origin checks and stale-response isolation.

## 5.0.4

- Align sidebar quick-search controls, compact shortcuts and icon spacing.
- Add opt-in contextual navigation folders with keyboard-operable Back controls and focus restoration.
- Preserve explicit KagNode brand marks on website links.

## 5.0.3

- Keep dedicated authentication pages free of public navigation sidebars.
- Reserve the expanded sidebar footprint during hover/focus expansion, so it does not cover page content.
- Include direct `#main` content wrappers in shared desktop and mobile layout rules.

## 5.0.2

- Preserve explicit Core icon hosts inside sidebar links, preventing a second automatic leading icon. Repeated normalization and dynamic icon changes retain one glyph.

## 5.0.1

- Honor reduced motion on the mobile drawer and avoid animating legacy panels during initial adoption.
- Keep nested-label input typography identical across login adapters and provide shared inline password-reveal and field-group templates.
- Preserve the existing right-facing disclosure-chevron alias when integrating original library glyphs.

## 5.0.0

- Establish the coordinated stable Core UI/adapter contract; explicit major-version adoption is required.
- Own the complete shared login frame, canonical KagNode mark, form controls, notices and recovery links.
- Use selected original 320-library glyphs in navigation and common actions, with a recorded alias-to-source map and optional remaining catalog.
- Add browser and Python decorative icon rendering; preserve locally served signed assets, immutable old asset URLs and independently reviewed manager policy.

## 1.4.0 — optional icon library preview

- Add 320 original outline UI icons in 16 searchable categories, each with a stable ID, title, tags and locally downloadable SVG.
- Ship a separate optional icon package with typed single-glyph imports, tree-shakable category exports and accessible decorative/titled rendering. Default UI assets and embedded adapter payloads do not load the expanded library.
- Include a responsive local gallery comparing 16/20/24 pixels, closed-grammar SVG validation, safety/geometry tests and Chromium/WebKit keyboard/mobile checks. Preserve KagNode Logos attribution separately.

## 1.3.1

- Keep account popovers inside the viewport when an application places its trigger near either edge. Size the shared component independently of host box-sizing rules.
- Dismiss the account menu when focus moves into an embedded document without stealing focus back from it.
- Add Chromium/WebKit regressions for left/right trigger placement, outside-click and iframe dismissal across phone, tablet and desktop widths.

## 1.3.0 (preview)

- Add an opt-in server-rendered login frame and shared provider CTA/status presentation and optional host-adapted approval/cancel controller, preserving authorized local forms and routes.
- Batch scroll discovery and scope sidebar refresh to its changed subtree.
- Refresh generated account identity email, skip hidden menu actions during keyboard navigation and close account popovers for modal dialogs.
- Keep account action controls at the shared 8px radius.

## 1.2.8 — backend-manager preview

- Reject FIFO, linked, nonregular, foreign-owned and writable lock controls without blocking or modifying their targets. New regular controls use mode 0600; safe existing controls retain their contents, inode and mode.
- Close daemon lock descriptors on startup failure as well as shutdown, retaining real contention behavior. Keep the scheduler alive when an unsafe control prevents recording an update error.
- Publish for explicit backend review; browser assets and automatic stable UI patch policy are unchanged.

## 1.2.7

- Keep a newly reopened quick search active when the previous native close event arrives late. Its debounce/request and focus remain current; normal dismissal still cancels pending work and restores focus.
- Add repeated native close/reopen and cancellation regressions for Chromium/WebKit across phone, tablet and desktop layouts.

## 1.2.6

- Preserve native date/date-time interval, precision and range validity in custom fields, including dynamic step changes. Invalid interval values block form submission; valid seconds remain accepted.
- Add Chromium/WebKit date-constraint and submission regressions across phone, tablet and desktop layouts.

## 1.2.5

- Preserve an enabled calendar keyboard stop at minimum/maximum date boundaries. Arrow navigation skips disabled dates without changing the selected value; Enter remains the explicit selection action.
- Add Chromium/WebKit date and date-time range, selection and focus-restoration regressions across phone, tablet and desktop layouts.

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
