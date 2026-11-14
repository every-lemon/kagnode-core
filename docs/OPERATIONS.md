# Updates and release operations

Build/test source before release. Run `npm run build` at the reviewed source commit, then `python3 tools/package.py --output release --signing-key /protected/signing.key`. The source commit in the signed manifest identifies the input source. Keep the signing key offline or in trusted release-only secret storage; never commit it or pass it to pull-request jobs. Publish packages, checksums and `core-manifest.json` plus `core-manifest.sig` together on `vVERSION`. Stable UI releases must pass browser and adapter checks before publication. Application integrations remain separately reviewed previews.

Install the manager from the reviewed wheel or CLI; bind an application using `sudo kagnode core bind APP --user SERVICE_USER --lock-file /path/to/app/core.lock.json`. An explicit `--baseline VERSION` is also supported for older integrations. A baseline is required; the manager never silently selects an old minor line. Existing service users and database paths stay unchanged. Run `sudo kagnode core serve` using the provided systemd service. Bind new applications before restarting the manager so their protected sockets can be created. The manager checks every six hours plus jitter. Ordinary users have no update authority.

Commands: `kagnode core status APP`, `check APP`, `apply APP --release-id ID`, `policy APP --automatic off`, and `rollback APP`. Privileged mutations require root or the existing app's private manager socket. The web UI applies the application's local administrator and CSRF checks before forwarding requests.

The baseline permits only its stable major.minor patch line. Downloads are bounded, verified and staged; activation atomically replaces a small state file. UI patches contain only listed JS/CSS/SVG/font files. No hooks execute, no app files change and no services restart. Errors remain in status. Interrupted staging never changes the active version. Old bundles remain available for open pages; administrators may archive them only after all applications and open sessions no longer need them.

Rollback validates the previous release (or returns to the embedded baseline) and pauses automatic updates. Keep the prior app deployment and database backup for application-level rollback. A Core UI rollback does not undo an application migration. Key rotation requires an explicitly reviewed adapter update containing the new public key; changing a downloaded manifest cannot replace trust.

Background checks skip applications while a manual operation holds the update lock. Failure status is recorded only after acquiring that same lock and reading the current state. Busy operations are retried on the next scheduled cycle; they are not reported as update failures. This manager change requires reviewed server-side installation and is not applied by a UI-only patch.

Privileged status and daemon startup reconcile interrupted update journals only after acquiring the update lock. A live updater's journal and staging files remain untouched. If activation already finished, recovery verifies the signed local cache offline before reporting completion; otherwise it reports interruption and retains the selected UI and update policy. Recovery never activates a downloaded release. Retry check/apply, or repeat the reviewed adoption for a baseline upgrade. Only temporary directories carrying this manager's matching ownership marker are removed; unmarked directories, symlinks and release caches are retained. Unprivileged CLI status requests privileged verification without modifying root-owned state.

## Reviewed application upgrades

Before replacing an application's source, run `sudo kagnode core check APP` and `sudo kagnode core apply APP` to verify/cache its current compatible UI. Manual apply also caches a current release without changing its activation or discarding the previous rollback pointer. Keep the application's own source/database rollback copy.

After reviewing and installing the application upgrade, inspect its `core.lock.json` and the current `kagnode core status APP`. Adopt its declared baseline explicitly:

```sh
sudo kagnode core adopt APP --lock-file /path/to/app/core.lock.json --expected-baseline OLD_BASELINE
```

This root-only CLI operation verifies the current and exact target stable UI releases using the fixed Core repository and signing key. It rejects stale baselines, changed declarations, wrong source commits and unavailable rollback assets before changing activation. It preserves existing service identities and a disabled automatic-update policy; declarations can also disable automatic updates. Same-line upgrades retain a newer installed patch. No backend hook runs and no application or native service restarts. This operation is intentionally unavailable through web-manager sockets, so compatible web UI updates cannot cross a minor-version boundary.

`rollback APP` restores the prior verified UI and pauses automatic updates. It does not undo application code or data migrations. The reviewed new baseline remains recorded; resuming automatic updates may return to that reviewed line. To roll back application code as well, restore its reviewed deployment and explicitly adopt its matching lock declaration. Older signed bundles remain cached for open pages and subsequent recovery.

Core 1.2.0's server manager must be installed through reviewed deployment or an updated CLI. Publishing a Core UI release cannot install this helper automatically. Existing application bindings and their patch lines are unchanged until an explicit adoption.

## Backend manager lock preview (1.2.8)

This preview requires explicit local-administrator review and installation, separate from compatible automatic UI patches. It does not run backend hooks, migrate application data or qualify native services. GitHub prerelease selection keeps it outside automatic stable UI activation.

The operation and daemon locks use nonblocking, no-follow descriptors and validate regular type, single link, current ownership and absence of group/other write permissions. The descriptor is validated again after opening. New controls are created with mode 0600. Safe existing regular controls, including legacy 0644 files, keep their bytes, inode and permissions. Unsafe controls are rejected rather than replaced, truncated, chmodded or repaired. A lock file belongs in protected manager storage; this is recovery robustness, not a claim that an unprivileged remote user can alter that storage.

A failed daemon startup closes its lock even while an exception traceback remains referenced. An unrecordable lock/state error is logged without writing state or terminating the scheduler, allowing a later retry after explicit repair. Existing exclusive contention stays busy; no lock is bypassed or broken. Do not remove an active lock to force an update. Tests use bounded disposable subprocesses for FIFOs and preserve existing targets, with no running manager or application changes.

## Optional authenticated update summaries (5.0.6)

This additive capability requires explicit installation of the reviewed 5.0.6
manager and server adapter. A UI patch cannot install those backend files. Old
helpers ignore optional signed metadata and show no invented update event.
The signed manifest may contain `user_summary:{title,items}`: bounded plain text,
never HTML. Only a successful changed automatic compatible UI patch records an
activation. Initial bundles, manual application, failed/interrupted installs and
rollback do not generate a new summary. Cached assets and signatures are
rechecked before a summary is served.

Local administrators may set `policy APP --summaries off` independently of
`--automatic on|off`; summaries default on. Admin status advertises
`capabilities.update_summaries`. The private socket's `summary` action returns
only `{available,notice}`; no paths, errors, repository configuration or update
authority are exposed to ordinary users.

Authenticated hosts supply persistent per-local-subject receipt callbacks:
Python `read_notice(app_id, subject, is_dismissed)` and
`dismiss_notice(app_id, subject, id, save_dismissed)`; Node uses asynchronous
`readNotice`/`dismissNotice` equivalents. Read callbacks receive `(subject,id)`;
save callbacks receive the same pair. IDs are immutable local user IDs, not
unverified email addresses. Preserve receipt data with account data. Flask
`register_flask_api` accepts `notice_subject`, `notice_is_dismissed`,
`notice_dismiss` and an optional `notice_write_guard`. Ordinary notice dismissal
must use the host's CSRF boundary, not its separate administrator-only
`write_guard`. Existing administrator actions retain their authorization.

Expose GET `/api/v1/kagnode-core/whats-new` and CSRF-protected POST
`/api/v1/kagnode-core/whats-new/dismiss` with `{id}`. Unavailable/static/embedded
hosts return `{available:false,notice:null}` and do not invent accounts or policy
controls. A malformed, stale or other activation ID cannot mark a new update as
read. The browser opts in only when fully authenticated and unlocked:
`KagNodeWhatsNewHost={ready:()=>true,headers:async()=>csrfHeaders}` followed by
`KagNodeWhatsNew.refresh()`. Alternatively set `data-core-notices="enabled"` on
body only while ready. No opt-in means no requests. Prompts wait for dialogs,
loading and edited forms to finish; dispatch `kagnode:form-saved` from the saved
form (or provide `detail.form`). Account switching cancels pending responses.

## Stable and Beta channels

Each application's Core binding has an independent channel and update mode. Existing automatic settings are retained; channel defaults to Stable. Beta admits signed `5.0.N-beta.M` releases plus stable releases, within the declared patch range. Application baselines and backend adapters still require explicit review and stable versions. Changing channel never downgrades an installed release.

Use `kagnode core policy APP --channel stable|beta --automatic on|off`. Local administrator controls expose the same policies after the reviewed manager upgrade. Old managers do not advertise channel controls. Automatic Core updates remain UI-only: no backend hooks, native package transactions or service restarts.
