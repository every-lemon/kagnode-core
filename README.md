# KagNode Core

Shared web components and local asset delivery for the KagNode ecosystem.

## Overview

Core provides the common interface for KagNode websites and independently hosted applications. Application servers serve a pinned local bundle; browsers never need GitHub to start the interface. Application authorization and business rules remain in the host project.

## Release status

**1.3.0 is a shared-login UI preview**, distributed as a prerelease for explicit application review. It adds the opt-in [login frame](docs/LOGIN.md), scoped scroll refresh and account-menu fixes. Existing compatible stable channels and backend installation policies remain unchanged.

**1.2.8 is a backend-manager preview**, distributed as a GitHub prerelease for explicit local-administrator review. It repairs unsafe lock-file handling without changing browser components. Compatible stable UI channels remain separate; automatic UI patching does not install this preview or upgrade backend helpers.

The initial 1.0 interface contract supports compatible stable UI patches. Application integrations are previews until their own checks and rollout are complete. Core release status does not qualify VPN networking, Mail delivery, Media codecs, HTTP Boot images or Bitwarden compatibility.

## Features

- One shared 260/57px sidebar, mobile drawer, icon account menu and restrained motion.
- Native wheel, touch and trackpad scrolling with accessible draggable rails.
- Shared fields, selectors, calendars, dialogs, loading, search, dashboard presentation and account preferences.
- Browser-to-account appearance connections with PKCE and origin-bound, revocable appearance-only grants.
- Offline adapters, signed UI-only updates, local administrator controls and rollback.

## Requirements

Node.js 24 for Node hosts/builds; Python 3.10+ for Python adapters. Flask is optional for its adapter. The Linux asset manager requires OpenSSL, root-owned storage and Unix sockets. Browser functionality progressively enhances ordinary authorized HTML. Reduced motion, forced colors and native-scrolling preferences are supported.

## Installation and downloads

| Package                                       | Platform       | Purpose                                                             |
| --------------------------------------------- | -------------- | ------------------------------------------------------------------- |
| `kagnode-core-V-node.tgz`                     | Node.js 24     | npm-compatible local adapter and pinned fallback                    |
| `kagnode_core-V-py3-none-any.whl`             | Python 3.10+   | Python adapter, manager and pinned fallback                         |
| `kagnode-core-V-ui.tar.gz`, `.tar.xz`, `.zip` | Browser assets | Versioned assets; only the signed tar.gz is installed automatically |
| `kagnode-core-V-source.*`                     | Any            | Editable source, tests, licenses and documentation                  |

Use [releases](https://github.com/every-lemon/kagnode-core/releases). Verify `SHA256SUMS`; the manager additionally verifies the detached Ed25519 signature on `core-manifest.json`. Never substitute a third-party repository or an unverified manifest.

## Usage

Node: install the local npm archive, then call `installCore(app, {appId, context})` before routes. Python: install the wheel, then call `register_flask(app, app_id, context)` before request handling. See [integration](docs/INTEGRATION.md). Existing authorized navigation and content are adopted into the canonical browser shell; adapters do not grant access or build private navigation.

## Configuration and storage

Applications commit `core.lock.json` with their baseline, adapter and compatible patch line. The manager stores immutable asset releases in `/srv/kagnode/core/releases/` and per-application bindings under `apps/`. Application databases, account passwords, encryption keys, native services and uploaded files remain in their existing locations. The bundled fallback starts offline even if the manager is unavailable.

## Security

Only compatible stable UI asset patches are automatic. They cannot contain backend hooks or restart services. Backend helpers, prereleases and minor/major changes require application review. The manager enforces fixed repository selection, signed inventories, bounded downloads, path checks, checksums, root ownership and per-app Unix socket permissions. Host applications must enforce local administrator authorization and CSRF. [Security details](docs/SECURITY.md).

Browser code is inspectable. Minification, fingerprints and attribution reduce accidental reuse; they do not make UI code copy-proof. Artwork permissions are separate from AGPL software licensing.

## Development and testing

Run `npm ci`, `npm run build`, `npm test`, `npm run check` and `npm run format:check`. Browser acceptance runs with `python tests/browser.py` after installing Playwright browsers. Set `KAGNODE_BROWSER_ENGINE=webkit` for WebKit. Tests use isolated fixtures rather than production accounts or media processing.

Build release archives with `python3 tools/package.py`. Signing is a separate trusted maintainer operation; private keys never belong in the repository. See [release operations](docs/OPERATIONS.md).

## Documentation

- [Repository map](docs/REPOSITORY-MAP.md)
- [Integration and component contract](docs/INTEGRATION.md)
- [Appearance connection protocol](docs/APPEARANCE.md)
- [Update operations and rollback](docs/OPERATIONS.md)
- [Artwork provenance](assets/provenance.json)
- [Component example](examples/server.mjs)
- [Changelog](CHANGELOG.md)

## Licensing

Software is AGPL-3.0-only; see [LICENSE](LICENSE). Imported KagNode artwork retains [its artwork permission](assets/ARTWORK-LICENSE). Public source and vendored corresponding source remain available with application packages.
