/*! KagNode Core — optional host-owned login connection presentation. */
(() => {
  if (window.KagNodeLogin) return;
  const completed = new WeakSet();
  let current = null,
    generation = 0;
  const clear = () => {
    if (!current) return;
    clearTimeout(current.timer);
    clearTimeout(current.expiryTimer);
    current.button.disabled = false;
    current.button.removeAttribute("aria-busy");
    current = null;
  };
  function status(state, message) {
    state.status.replaceChildren(document.createTextNode(message));
  }
  function terminal(state, message) {
    if (current !== state) return;
    generation++;
    status(state, message);
    clear();
  }
  async function receive(state, result) {
    if (current !== state || state.generation !== generation) return;
    if (result?.authorized === true) {
      status(state, "Identity confirmed. Continuing…");
      try {
        await state.host.complete(result);
        if (current === state) {
          generation++;
          clear();
          completed.add(state.button);
          state.button.disabled = true;
        }
      } catch {
        terminal(state, "Unable to continue. Try again or sign in locally.");
      }
      return;
    }
    if (!result?.pending) {
      terminal(
        state,
        "Connection was not approved. Try again or sign in locally.",
      );
      return;
    }
    if (!state.attempt) {
      if (
        typeof result.attempt_id !== "string" ||
        !result.attempt_id ||
        typeof result.user_code !== "string"
      )
        return terminal(
          state,
          "Unable to connect. Try again or sign in locally.",
        );
      let link;
      try {
        link = new URL(result.verification_uri);
        if (link.protocol !== "https:" || link.username || link.password)
          throw Error("Invalid verification link");
      } catch {
        return terminal(
          state,
          "Unable to connect. Try again or sign in locally.",
        );
      }
      state.attempt = result.attempt_id;
      const lifetime = Number(result.expires_in);
      state.deadline =
        Date.now() +
        Math.min(600, Math.max(1, Number.isFinite(lifetime) ? lifetime : 300)) *
          1000;
      clearTimeout(state.expiryTimer);
      state.expiryTimer = setTimeout(
        () =>
          terminal(state, "Connection expired. Try again or sign in locally."),
        Math.max(1, state.deadline - Date.now()),
      );
      state.interval =
        Math.min(30, Math.max(1, Number(result.interval) || 3)) * 1000;
      status(state, "Confirm this code with KagNode: ");
      const code = document.createElement("strong");
      code.textContent = result.user_code;
      const verification = document.createElement("a");
      verification.href = link.href;
      verification.target = "_blank";
      verification.rel = "noopener noreferrer";
      verification.textContent = "Open KagNode to approve";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "Cancel connection";
      cancel.addEventListener("click", () => {
        if (current !== state) return;
        const attempt = state.attempt;
        terminal(
          state,
          "Connection cancelled. You can try again or sign in locally.",
        );
        state.button.focus({ preventScroll: true });
        Promise.resolve()
          .then(() => state.host.request("cancel", { attempt_id: attempt }))
          .catch(() => {});
      });
      state.status.append(
        code,
        document.createTextNode(" "),
        verification,
        document.createTextNode(" "),
        cancel,
      );
    }
    state.timer = setTimeout(
      async () => {
        if (current !== state) return;
        if (Date.now() >= state.deadline)
          return terminal(
            state,
            "Connection expired. Try again or sign in locally.",
          );
        try {
          await receive(
            state,
            await state.host.request("status", { attempt_id: state.attempt }),
          );
        } catch {
          terminal(
            state,
            "Unable to check the connection. Try again or sign in locally.",
          );
        }
      },
      Math.min(state.interval, Math.max(1, state.deadline - Date.now())),
    );
  }
  document.addEventListener("click", async (event) => {
    const button = event.target.closest?.("button[data-core-login-provider]");
    const host = window.KagNodeLoginHost;
    if (!button || !host?.request || !host?.complete) return;
    const container = button.closest("[data-core-login]");
    const output = container?.querySelector("[data-core-login-status]");
    if (
      !output ||
      current ||
      completed.has(button) ||
      host.state?.()?.enabled === false
    )
      return;
    event.preventDefault();
    const state = { button, status: output, host, generation: ++generation };
    current = state;
    state.expiryTimer = setTimeout(
      () => terminal(state, "Unable to connect. Try again or sign in locally."),
      30000,
    );
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    output.setAttribute("role", "status");
    status(state, "Connecting with KagNode…");
    try {
      await receive(state, await host.request("start", {}));
    } catch {
      terminal(state, "Unable to connect. Try again or sign in locally.");
    }
  });
  function refresh() {
    const host = window.KagNodeLoginHost;
    if (!host) return;
    for (const button of document.querySelectorAll(
      "button[data-core-login-provider]",
    ))
      if (button !== current?.button)
        button.disabled =
          completed.has(button) || host.state?.()?.enabled === false;
  }
  window.KagNodeLogin = { refresh };
  document.addEventListener("kagnode:login-ready", refresh);
  refresh();
  addEventListener("pagehide", () => {
    generation++;
    clear();
  });
})();
