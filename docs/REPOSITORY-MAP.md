# Repository map

| Path               | Contents                                                                            |
| ------------------ | ----------------------------------------------------------------------------------- |
| `web/`             | Editable browser components, motion, tokens and page presentation                   |
| `packages/node/`   | Express/local asset adapter and type declarations                                   |
| `packages/python/` | Python/Flask adapter and Linux signed UI manager                                    |
| `assets/`          | Imported approved marks, icon definitions, public signing key and provenance        |
| `tools/`           | Build, deterministic packaging and vendor synchronization                           |
| `dist/`            | Generated fingerprinted assets and offline adapters; regenerate rather than editing |
| `tests/`           | Isolated adapter, security, manager and browser fixtures                            |
| `examples/`        | Runnable local component examples                                                   |
| `docs/`            | Integration, appearance protocol and maintainer operations                          |

Application business rules stay in their own repositories. The Logos repository remains the canonical artwork collection. Runtime caches, credentials and deployment backups are never source files.
