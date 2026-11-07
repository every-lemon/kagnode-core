# Appearance-only account connection

Signed-out pages follow the system theme. Local-only signed-in accounts use a subject-scoped browser preference. First-party sites use their authenticated `/api/account/appearance` route and CSRF protection. Independent origins connect directly to the account issuer, without sending credentials through the application server.

1. The browser creates a random PKCE verifier/state in memory and an S256 challenge. A popup opens `/auth/appearance/authorize` with the exact application origin.
2. KagNode authenticates the account and asks for appearance-only consent. A 120-second, single-use authorization code is returned with `postMessage` to that exact origin. The client validates opener, issuer, state and local account.
3. The browser exchanges the code/verifier at `/api/v1/appearance/token`. Access tokens last ten minutes and remain in memory. The thirty-day appearance-only renewal handle rotates on use. Hashes, not raw tokens, are stored by KagNode.
4. GET/PATCH `/api/v1/appearance/preferences` returns theme and `version`. Writes require the current version; conflicts refresh the value instead of overwriting silently. CORS is origin-bound and carries no account cookies.
5. Tokens cannot read profile data, roles, email, vault data or application APIs. Refresh reuse revokes that connection. Account suspension, session reset and explicit revocation stop access.

Synchronization occurs on connection, focus and a modest interval. Tabs coordinate refresh using Web Locks and BroadcastChannel. Network failures retain the last valid appearance; disconnecting or expiry never blocks local authentication or vault access. Account settings on the issuer show origin connections with individual revocation. Independent applications also offer Disconnect.

The appearance grant is separate from server-side profile linking and its administrator policy. Servers never receive the browser appearance token. Any script running in the same application origin can access that origin's appearance preference storage; use a trusted HTTPS origin and a restrictive CSP. No vault credential is reused for this purpose.
