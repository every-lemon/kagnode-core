# Navigation performance evidence

The 1.3 preview scopes sidebar rail discovery to the sidebar (or changed group) and batches requests per animation frame. Full refresh remains available and is retained on viewport resize. Mutation discovery targets the changed subtree rather than rescanning the whole page after a fixed timer.

A same-host Chromium probe used a 1440×900 viewport, 1,000 unrelated content rows, 20 navigation links and 20 actual toggle clicks, one per animation frame. It wrapped the native `clientHeight`, `clientWidth`, `scrollHeight` and `scrollWidth` getters, `getComputedStyle` and `getBoundingClientRect` after initial settling. The baseline was source commit `4f3237a` (1.2.8). Both runs finished expanded.

| Counter                  |   Before |    After |
| ------------------------ | -------: | -------: |
| Layout dimension reads   |   82,880 |    2,300 |
| Computed style calls     |      320 |      321 |
| Bounding rectangle calls |       60 |       60 |
| Discovery subtree scans  |       20 |       20 |
| Frame-paced wall time    | 335.56ms | 335.55ms |

The measured change removes 97.2% of dimension reads for this fixture. The frame-paced elapsed time is essentially unchanged; this is evidence of reduced discovery work, not a claim of faster network loading or a general wall-clock speedup. Scan count is unchanged because each click occurred in a separate frame; each scan now visits the small sidebar instead of unrelated content.

Run `python tests/scroll_performance_probe.py` with Playwright Chromium installed to repeat the source-level probe. `tests/login_performance_browser.py` also checks a bundled fixture in Chromium/WebKit with a conservative read-count bound and functional login, cancellation/stale-result, menu, mobile, offline-asset and focus checks. The bundled fixture includes additional account/dialog nodes and measured approximately 2,460 dimension reads for 20 toggles. The existing browser suite exercises repeated group animation, native wheel/rail input, reduced motion, drawers and dialogs across ten viewport/theme layouts per engine.
