# Core delivery: community and business editions

Status: design and reference tool. Source implemented in `tools/corereq.mjs` with tests. The Daemon side and the server side are not built yet. The first business release is `core-be-5.0.20-beta`.

## Two editions

|                | Community (`ce`)                                | Business (`be`)                         |
| -------------- | ----------------------------------------------- | --------------------------------------- |
| Source         | Public, full Core in this repository            | Private, kept on KagNode servers        |
| Looks          | The current public interface                    | The new interface (Apple-style preview) |
| Default        | Yes. Tested, maintained and bug-fixed in public | Only when a deployment asks for it      |
| Delivered from | GitHub release assets, signature checked        | KagNode servers, signature checked      |

The community edition never depends on the business edition. A deployment that asks for the business edition and cannot get it keeps working on files it already has, or on the community fallback it named.

## Names

`core-[ce|be]-x.x.x-[alpha|beta]`, with the channel left out for a release.

`core-ce-5.0.19`, `core-be-5.0.20-beta`, `core-be-6.0.0-alpha`. Order for the same x.x.x: alpha, beta, release. Existing releases (5.0.x) are community. Source: `parseName`, `coreName`, `compareNames`.

## Branches in this repository

- Community branch (the default): the full Core, as today.
- `be` branch: one file, `corereq.txt`. Template: `docs/be-branch/corereq.txt`. A user who wants the business edition takes this file; it holds no interface code.

## corereq.txt

Plain text, line by line, `#` for comments. Unknown keys are rejected, so a typo can never widen a request.

```
corereq 1
name core-be-5.0.20-beta
product passwords
fallback core-ce-5.0.19
need mark
need script
need style
need theme
```

| Key           | Meaning                                                                                                                                                             |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `corereq 1`   | Format version. First line.                                                                                                                                         |
| `name`        | Core name, as above.                                                                                                                                                |
| `server`      | Business only. The https address of the KagNode core server. A community core never has one.                                                                        |
| `signing-key` | Business only. `ed25519:` plus the base64 public key the Daemon uses to verify everything the server returns. Public, not a secret. A community core never has one. |
| `product`     | Optional. Which deployment is asking.                                                                                                                               |
| `fallback`    | Optional. A community core to use if the business files cannot be obtained. Must be `ce`.                                                                           |
| `need`        | One per file role the deployment uses: `theme`, `script`, `style`, `mark`, `bundle`, `icons/<category>`. Nothing else is ever sent to it.                           |
| `have`        | Added by the Daemon when it asks the server: a role it already holds and that file's `sha256`.                                                                      |

The file contains no secrets. The `signing-key` is the public half of a key pair; the private half stays on KagNode's servers. Entitlement comes from the licence code held by the Daemon, never from corereq.txt. The corereq.txt a user gets from the public repository's community side has no `server` and no `signing-key`: the Daemon pulls that core from GitHub.

## Licence check (business only)

1. The Daemon reads `server` and `signing-key` from corereq.txt.
2. It asks the administrator for the licence code once, and keeps it in its own protected store.
3. It asks the server whether the code is available (valid, not revoked, not past its end date, installation count not exceeded) and sends an installation id with it. The server answers with a short lease: allowed or not, until when, and which versions.
4. Only if the lease says yes does the Daemon request the files (steps below). A lease that is not renewed by its end date stops new downloads and updates; it does not remove files already installed, and a named `fallback` keeps the product on the community interface.

## What the Daemon does

1. A deployment's entry in KagNode's package list points to its `corereq.txt`.
2. The Daemon reads the name. `ce`: pull from GitHub. `be`: pull from the KagNode servers. It never switches edition on its own.
3. For `be`, it first asks the server for the signed index of that version: each role with its `sha256` and size (small).
4. It compares the needed hashes with its shared Core store, which other deployments already filled. Files already there are reused (`plan`).
5. It sends the request with a `have` line for each reused file (`request`). The server answers with only the missing files, in a signed bundle.
6. It verifies the signature with the pinned key and every `sha256`, then stores each file by hash and links the deployment to them. Previous versions stay for rollback.

Result: two deployments that need the same `style` file store it once; a second deployment pulls only what the first did not.

## Failure rules

- Server unreachable or not entitled: keep serving the files already stored. If none and a `fallback` is named, use it. Otherwise report it, do not guess.
- A hash or signature mismatch deletes the download and is reported. Nothing partial is linked.
- Size caps apply to corereq.txt (64 KiB) and to each response.

## Reference tool

```
node tools/corereq.mjs make --edition be --version 5.0.20 --channel beta --product passwords --fallback core-ce-5.0.19
node tools/corereq.mjs index --dist dist > index.json
node tools/corereq.mjs plan --req corereq.txt --index index.json --store held-hashes.txt
```

The Daemon and the server implement the same rules in Rust. The tests in `tests/corereq.test.mjs` are the shared test cases.
