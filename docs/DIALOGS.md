# Shared form dialogs

Use `KagNodeDialogs.open(dialog, { initialFocus, returnFocus })` with a native `<dialog>` and a direct `<header>` containing its heading. Core supplies one accessible × button, closes the mobile drawer, traps modal focus through native dialog behavior, and restores focus on dismissal. Do not add a second close button in the host.

Core marks user-edited controls dirty. Clicking × or pressing Escape asks whether to discard changes; Keep editing retains the form. Programmatic `KagNodeDialogs.close(dialog)` after a successful save does not prompt. A `reset` clears dirty state. Applications can cancel `kagnode:dialog-beforeclose` when they need a specific dismissal policy.

On desktop (700px and wider), pointer dragging is restricted to the header background and heading, never its interactive controls. Pointer capture maintains the gesture, placement is clamped to the visible viewport, resizing re-clamps, and a mobile viewport removes custom placement. Every open starts centered; optional `sheet` keeps the established mobile sheet behavior. Dialog bodies retain native scrolling.

Reduced-motion preferences suppress entry animation. Close controls remain keyboard accessible. Applications own form validation, permissions, saving and server-side conflict handling.
