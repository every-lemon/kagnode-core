# Components

## Loading spinner

`KagNodeCore.loading.show("Opening your vault…")` and `hide()` control the full-screen loading surface. The split-orbit spinner keeps the canonical mark still. Reduced motion replaces rotation with a quiet localized breathing ring; the status label remains visible and announced. Do not use a loading state to imply measurable progress.

Use `KagNodeLoading.spinner()` for a decorative spinner node beside an accessible status label. Set `--kn-spinner-size` on its container to adjust the default 96px size. Add `data-core-loading` to an existing loading surface to adopt the shared spinner while preserving labels, retry buttons and dismissal controls. Core also recognizes the existing official, Passwords, Mail and Media loading surfaces. Existing operation controllers retain ownership of visibility and error recovery.

## Date and time constraints

Use semantic `date` or `datetime-local` fields with the application’s `min`, `max`, `step` and `required` constraints. Core preserves native date/precision/interval validity, including the value-based step origin, while presenting its calendar and editable field. Constraint changes refresh validation; valid seconds remain accepted when the declared step allows them. Invalid values block form submission. Applications must still validate submitted values on the server.

## Quick-search reopening

The palette can be reopened immediately after dismissal without an artificial delay. Queued native close events from an earlier opening do not cancel the current query or move its focus. Normal dismissal still cancels pending work and restores focus. Applications continue supplying authorized destinations and provider results.

### Contextual sidebar folders

Applications may opt in with one `[data-core-nav-root]` wrapper and named
`[data-core-nav-folder="plan"]` wrappers. Buttons with `data-core-nav-open="plan"`
open a folder; a `data-core-nav-back` button restores the root and keyboard
focus. Give open buttons `aria-controls` pointing to the folder's unique ID.
Place `data-core-nav-default="plan"` on the sidebar when the current route
belongs to that folder. Core manages visibility, focus and scroll measurement;
applications still supply authorized destinations and labels. Include a normal
reader/overview link for fallback navigation. Explicit website brand links use
`data-core-brand-link`, preserving their artwork instead of substituting a home
icon.

## Segmented views

Use `data-core-segments` on a labelled group, `data-core-segment="value"` on
buttons or real links, and matching `data-core-panel="value"` sections inside
`data-core-panels`. Core supplies a sliding indicator, roving keyboard focus,
Arrow/Home/End operation and reduced-motion behavior. Disabled controls are
skipped. Preserve real `href` destinations for server fallback.

A cancelable, bubbling `kagnode:segment-change` event carries
`{value, previous, url}`. Cancel it when an application owns authorized partial
navigation; Core does not fetch application content. Optional
`data-core-url-param="view"` with `data-core-history="push"` updates local-panel
query state and follows Back/Forward without replacing unrelated query/hash
values. Real links without local panels retain normal navigation.
`KagNodeSegments.refresh()` safely mounts dynamically added groups.

## Contextual loading and sheets

`const done = KagNodeLoading.begin({label:"Opening plan…", mode:"overlay"})`
returns an idempotent completion function. Call `done.update("Rendering…")` (or
`done.phase`) for a new phase and `done()` in `finally`. Independent operations
cannot dismiss one another. `mode:"topbar"` is nonblocking; `mode:"inline"`
requires a `target` element and restores its original `aria-busy` on completion.
The existing `show/hide` API remains supported. Overlays cover custom rails and
remain visible above a native open dialog. Keep labels specific to the work;
do not claim numeric progress from an indeterminate spinner.

`KagNodeDialogs.open(dialog,{sheet:true,returnFocus,initialFocus})` opens a native
modal dialog, closes competing navigation surfaces and restores focus on close.
Use `KagNodeDialogs.close(dialog)` or a button with `data-core-dismiss`. A button
with `data-core-dialog-open="dialog-id"` provides declarative opening. Compact
screens present `data-core-sheet` dialogs at the bottom; desktop uses the same
content as a dialog. Native Escape and reduced motion remain available.

Mark account photographs with `data-core-avatar`. The authenticated
`kagnode:avatar-changed` document event accepts `{subject,url}` only for the
current subject and existing same-origin photo delivery. An empty URL restores
initials. Avatar-only triggers are circular; menu rows retain their own shape.

## Browser motion verification

Core 5.0.6's motion acceptance uses pinned Playwright 1.64.1 Chromium and WebKit
(WebKit revision 2370), matching the local and protected CI runtimes. Delayed
native document GET/POST fixtures inspect multiple actual frames, including
normal spinner/track movement and quiet reduced-motion breathing. The older
Playwright 1.58 WebKit runtime failed the pending-document topbar motion gate;
continuous motion on that engine is not certified by this release. Loading
labels, native navigation and reduced-motion controls remain available; an
animation is never used as proof that a request completed.

## Preference actions and notice navigation (5.0.7)

The root `data-core-scroll-state` attribute reports runtime presentation only.
`button[data-core-scroll-mode]` is the explicit preference action; ordinary clicks
and keyboard activation of other controls never save a preference. Do not place
action attributes on page containers.

Background update-summary reads abort before native links/forms leave a document,
on pagehide/beforeunload, when hidden, and during active loading operations.
Intercepted navigation resumes after the host prevents the native event; pageshow
also resumes restored pages. Notice read generations are separate from session
and dismissal state. The loading component emits `kagnode:loading-operation`
with `{pending}` when its operation count changes, covering inline/topbar work as
well as overlays. This event does not grant update or authentication authority.

## Component-status reads (5.0.8)

The background management-status request shares one cancellation context across
its preliminary local CSRF/session read and final status read. Native navigation,
pagehide and session changes invalidate the full chain; stale errors or results
cannot overwrite a newer account. Hidden/loading pages defer background reads,
and restored pages resume reads only. Background refresh never opens interactive
reauthentication.

Explicit administrator actions own their loading operation. Navigation/session
interruption cancels their continuation and does not automatically replay check,
apply, policy or rollback requests. A server may have accepted an interrupted
request; inspect its persistent status before deliberately retrying. An explicit
reauthentication continuation must still match the original session and signal.
