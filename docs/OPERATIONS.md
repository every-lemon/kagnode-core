# Updates and release operations

Build/test source before release. Run `npm run build` at the reviewed source commit, then `python3 tools/package.py --output release --signing-key /protected/signing.key`. The source commit in the signed manifest identifies the input source. Keep the signing key offline or in trusted release-only secret storage; never commit it or pass it to pull-request jobs. Publish packages, checksums and `core-manifest.json` plus `core-manifest.sig` together on `vVERSION`. Stable UI releases must pass browser and adapter checks before publication. Application integrations remain separately reviewed previews.

Install the manager from the reviewed wheel or CLI; bind an application using `sudo kagnode core bind APP --user SERVICE_USER --lock-file /path/to/app/core.lock.json`. An explicit `--baseline VERSION` is also supported for older integrations. A baseline is required; the manager never silently selects an old minor line. Existing service users and database paths stay unchanged. Run `sudo kagnode core serve` using the provided systemd service. Bind new applications before restarting the manager so their protected sockets can be created. The manager checks every six hours plus jitter. Ordinary users have no update authority.

Commands: `kagnode core status APP`, `check APP`, `apply APP --release-id ID`, `policy APP --automatic off`, and `rollback APP`. Privileged mutations require root or the existing app's private manager socket. The web UI applies the application's local administrator and CSRF checks before forwarding requests.

The baseline permits only its stable major.minor patch line. Downloads are bounded, verified and staged; activation atomically replaces a small state file. UI patches contain only listed JS/CSS/SVG/font files. No hooks execute, no app files change and no services restart. Errors remain in status. Interrupted staging never changes the active version. Old bundles remain available for open pages; administrators may archive them only after all applications and open sessions no longer need them.

Rollback validates the previous release (or returns to the embedded baseline) and pauses automatic updates. Keep the prior app deployment and database backup for application-level rollback. A Core UI rollback does not undo an application migration. Key rotation requires an explicitly reviewed adapter update containing the new public key; changing a downloaded manifest cannot replace trust.

Background checks skip applications while a manual operation holds the update lock. Failure status is recorded only after acquiring that same lock and reading the current state. Busy operations are retried on the next scheduled cycle; they are not reported as update failures. This manager change requires reviewed server-side installation and is not applied by a UI-only patch.

## Reviewed application upgrades

Before replacing an application's source, run `kagnode core check APP` and `sudo kagnode core apply APP` to verify/cache its current compatible UI. Manual apply also caches a current release without changing its activation or discarding the previous rollback pointer. Keep the application's own source/database rollback copy.

After reviewing and installing the application upgrade, inspect its `core.lock.json` and the current `kagnode core status APP`. Adopt its declared baseline explicitly:

```sh
sudo kagnode core adopt APP --lock-file /path/to/app/core.lock.json --expected-baseline OLD_BASELINE
```

This root-only CLI operation verifies the current and exact target stable UI releases using the fixed Core repository and signing key. It rejects stale baselines, changed declarations, wrong source commits and unavailable rollback assets before changing activation. It preserves existing service identities and a disabled automatic-update policy; declarations can also disable automatic updates. Same-line upgrades retain a newer installed patch. No backend hook runs and no application or native service restarts. This operation is intentionally unavailable through web-manager sockets, so compatible web UI updates cannot cross a minor-version boundary.

`rollback APP` restores the prior verified UI and pauses automatic updates. It does not undo application code or data migrations. The reviewed new baseline remains recorded; resuming automatic updates may return to that reviewed line. To roll back application code as well, restore its reviewed deployment and explicitly adopt its matching lock declaration. Older signed bundles remain cached for open pages and subsequent recovery.

Core 1.2.0's server manager must be installed through reviewed deployment or an updated CLI. Publishing a Core UI release cannot install this helper automatically. Existing application bindings and their patch lines are unchanged until an explicit adoption.
