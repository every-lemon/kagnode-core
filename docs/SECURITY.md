# Security boundaries

The application decides who may sign in, navigate, view private content and manage updates. Core does not expand roles. Navigation sent to an unauthorized browser must not contain private links even when visually hidden. Keep application-specific administration assets on protected routes.

The manager accepts only the fixed KagNode Core repository, trusted HTTPS download hosts and a verified Ed25519 manifest. It checks inventory, content hashes, sizes, archive paths/types and API compatibility. Socket ownership and peer UID bind actions to an application process. Host authorization/CSRF remains mandatory, since the application process is trusted to act for its own administrators.

The update channel can replace browser UI code. Treat its signing key as a software supply-chain credential. Maintain independent backup and rollback copies. The bundled baseline starts without network access. An unsigned or incompatible release cannot become an automatic patch.

Source archives and application fallbacks include corresponding editable source and licenses. Public source contains no deployment keys, production database, vault secret or operator-specific logo. Report security concerns privately to repository maintainers rather than posting credentials in an issue.
