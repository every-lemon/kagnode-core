# Components

## Loading spinner

`KagNodeCore.loading.show("Opening your vault…")` and `hide()` control the full-screen loading surface. The split-orbit spinner keeps the canonical mark still. Reduced motion stops the orbit; the status label remains visible and announced. Do not use a loading state to imply measurable progress.

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
