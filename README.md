# KagNode. Core

Shared web components and local asset delivery for KagNode applications.

![Services page in light mode with the shared sidebar, table and status dots](docs/images/core-desktop-light.png)

## Overview

Core gives every KagNode site the same shell: sidebar, account menu, search, dialogs, form controls, loading states and login frame. Your application serves a pinned, verified bundle from its own origin. Authorization, data and business rules stay in the application.

| Light                                        | Dark                                       | Phone                                 |
| -------------------------------------------- | ------------------------------------------ | ------------------------------------- |
| ![Light](docs/images/core-desktop-light.png) | ![Dark](docs/images/core-desktop-dark.png) | ![Phone](docs/images/core-mobile.png) |

Screenshots show the unreleased 5.0.20 styling.

### How it works

| Step   | What happens                                                                                                            |
| ------ | ----------------------------------------------------------------------------------------------------------------------- |
| Serve  | An adapter (Node, Python or Rust) copies the pinned bundle onto your server.                                            |
| Draw   | Core wraps your HTML in the shared shell. You supply links, content and visibility.                                     |
| Update | A manager checks a detached signature and checksums, keeps the previous bundle, and applies only compatible UI patches. |
| Extend | Tables, status dots, fact lists, meters and password-confirm dialogs use the same tokens.                               |

## Release status

|                 |                                                                           |
| --------------- | ------------------------------------------------------------------------- |
| Current release | 5.0.19 (published, deployed on the KagNode sites)                         |
| Next            | 5.0.20 candidate in draft, not released                                   |
| Not covered     | Application rules, VPN, Mail delivery, Media codecs, HTTP Boot, Bitwarden |

## Installation and downloads

| Package                           | For                              |
| --------------------------------- | -------------------------------- |
| `kagnode-core-V-node.tgz`         | Node.js 24 adapter               |
| `kagnode_core-V-py3-none-any.whl` | Python 3.10+ adapter and manager |
| `kagnode-core-V-rust.tar.gz`      | Rust 1.88+ adapter               |
| `kagnode-core-V-ui.tar.gz`        | Browser assets (signed)          |
| `kagnode-core-V-icons.*`          | Optional icon library            |
| `kagnode-core-V-source.*`         | Source, tests, licenses          |

Take releases only from [GitHub releases](https://github.com/every-lemon/kagnode-core/releases). Verify `SHA256SUMS`; the manager also verifies the Ed25519 signature on `core-manifest.json`.

## Usage

| Host   | Call                                                        |
| ------ | ----------------------------------------------------------- |
| Node   | `installCore(app, {appId, context})` before routes          |
| Python | `register_flask(app, app_id, context)`                      |
| Rust   | `Core::new(root, application)` and serve its checked assets |

Details: [integration](docs/INTEGRATION.md), [components](docs/COMPONENTS.md), [dialogs](docs/DIALOGS.md), [icons](docs/ICONS.md).

## Configuration and storage

| Item                    | Location                             |
| ----------------------- | ------------------------------------ |
| Baseline and patch line | `core.lock.json` in your application |
| Releases                | `/srv/kagnode/core/releases/`        |
| Per-app bindings        | `/srv/kagnode/core/apps/`            |
| Offline fallback        | Bundled with the adapter             |

## Security

Only compatible UI patches update automatically; they cannot restart services or add backend code. The manager enforces fixed repositories, signed inventories, bounded downloads, path checks and root ownership. Hosts enforce administrator authorization and CSRF. See [security](docs/SECURITY.md).

## Development and testing

```
npm ci && npm run build && npm test && npm run check && npm run format:check
python tests/browser.py        # KAGNODE_BROWSER_ENGINE=webkit for WebKit
```

## Licensing

Software: AGPL-3.0-only ([LICENSE](LICENSE)). Artwork: [ARTWORK-LICENSE](assets/ARTWORK-LICENSE).

## Links

|           |                                                                |
| --------- | -------------------------------------------------------------- |
| Changelog | [CHANGELOG.md](CHANGELOG.md)                                   |
| Releases  | [GitHub](https://github.com/every-lemon/kagnode-core/releases) |
