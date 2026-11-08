# Components

## Loading spinner

`KagNodeCore.loading.show("Opening your vault…")` and `hide()` control the full-screen loading surface. The split-orbit spinner keeps the canonical mark still. Reduced motion stops the orbit; the status label remains visible and announced. Do not use a loading state to imply measurable progress.

Use `KagNodeLoading.spinner()` for a decorative spinner node beside an accessible status label. Set `--kn-spinner-size` on its container to adjust the default 96px size. Add `data-core-loading` to an existing loading surface to adopt the shared spinner while preserving labels, retry buttons and dismissal controls. Core also recognizes the existing official, Passwords, Mail and Media loading surfaces. Existing operation controllers retain ownership of visibility and error recovery.
