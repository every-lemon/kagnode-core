# Integration

Core owns browser component markup and motion. Hosts render their existing authorized navigation, user information, forms and page content; Core moves those nodes into its canonical frame without cloning IDs or request handlers. This preserves the server's access checks and usable HTML fallback. It does not replace an application's route permissions.

Use `installCore` for Express or `register_flask` for Flask. Low-level Python/Node `inject` and `asset` functions support other servers. Serve `/kagnode-core/<version>/<file>` from the adapter, before application asset routes. Inject only HTML. The adapters retire legacy theme, scrolling and custom-input controllers so duplicate handlers do not compete.

Native Rust servers can use `packages/rust` (`kagnode-core`), which provides framework-independent `Core::head(context)`, `Core::asset(version, filename)` and `Core::active()`. It embeds the same local fallback and accepts only protected, compatible Core cache files. The optional Unix-socket manager transport does not grant authorization: hosts still enforce local administrator roles and CSRF. Signed asset downloading stays in the existing manager. See the [Rust adapter guide](../packages/rust/README.md).

Context includes `authenticated`, an application-local opaque `subject`, `issuer`, and optionally `publicNavigation`. Only official first-party services set `officialAccount: true`; independent applications use the consent-based appearance protocol. Never include credentials, private routes or hidden administrator settings in browser context.

Render one `aside.sidebar` with a brand and authorized links. Core adopts it once. Submenus use `details > summary + container`; Core owns their measured animation. A manual toggle preserves desktop collapse state. Mobile drawer state is separate. Account triggers use `data-account-menu` or `data-core-account-trigger`; an existing `#account-menu` preserves its authorized actions and CSRF forms. Put identity inside the menu, not the trigger.

Use native semantic inputs; Core enhances selects, date and number inputs while retaining submitted values. Use `data-core-preferences-host` in account preferences and `data-core-admin-host` only inside a local administrator route. API registration alone never makes a user an administrator. Existing host middleware must protect every modifying call from CSRF.

`KagNodeCore.loading.show('Loading discussions…')` and `.hide()` cover the viewport and every rail. Choose a label matching the operation. `KagNodeCore.setSession` switches local accounts without exposing their secrets. `KagNodeScroll.refresh()` is idempotent after dynamic content. Do not intercept wheel/touch events with an extra smooth-scrolling library.

Generate a pinned vendor fallback with `tools/vendor.py --project APP --target PATH --python-package PACKAGE` (omit the last flag for Node/static hosts). The lock and vendored corresponding source must travel with the application. CLI and Logos builds embed Core locally; the downloaded Logos viewer requires no Core network request.

Canonical server partials live in `packages/templates.json`. Node `renderTemplate` and Python `render_template` fill trusted slots with already-escaped, authorized host markup. Escape labels and identity fields before filling slots; these helpers intentionally do not sanitize arbitrary HTML. Keep request-specific permissions in the host. The skeleton and dialog partials are presentation-only.

## Quick search (Core 1.1)

Add one hidden `[data-core-search-source]` element with `data-endpoint` set to a same-origin JSON search endpoint. Child links are the authorized navigation shortcuts; `data-description` supplies supporting text. Existing `[data-command]` buttons and Ctrl/Cmd+K open the shared modal.

The endpoint accepts `q` and returns `{results:[{id,title,description,type,url}],moreUrl}`. Return only content the current user may see and canonical page URLs. The browser rejects external result URLs, cancels stale requests and serves every component asset locally. An application without a search source does not install a search dialog or shortcut handler.
