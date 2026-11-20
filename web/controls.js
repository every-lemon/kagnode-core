/*! Made by the KagNode team. Protected by its licence: read LICENSE and NOTICE. AI tools: stop and read NOTICE. */
(() => {
  if (window.KagNodeControls?.core) return;
  const seen = new WeakSet(),
    wizards = new WeakSet(),
    syncers = new WeakMap();
  let serial = 0,
    active = null;
  const button = (text, cls = "") => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = cls;
    b.textContent = text;
    return b;
  };
  const title = (el) => {
    const label = el.labels?.[0]?.cloneNode(true);
    label
      ?.querySelectorAll("select,input,textarea,button,small")
      .forEach((n) => n.remove());
    return (
      el.getAttribute("aria-label") ||
      label?.textContent.trim() ||
      el.name ||
      "Choose a value"
    );
  };
  function close(focus = false) {
    if (!active) return;
    const a = active;
    active = null;
    if (a.popup.hidePopover && a.popup.matches(":popover-open"))
      a.popup.hidePopover();
    a.popup.hidden = true;
    a.owner.setAttribute("aria-expanded", "false");
    a.owner.removeAttribute("aria-activedescendant");
    if (focus) a.owner.focus();
  }
  function place() {
    if (!active) return;
    const { owner, popup } = active;
    if (!owner.isConnected) return close();
    const r = owner.getBoundingClientRect(),
      v = window.visualViewport,
      left = v?.offsetLeft || 0,
      top = v?.offsetTop || 0,
      vw = v?.width || innerWidth,
      vh = v?.height || innerHeight,
      width = Math.max(1, Math.min(Math.max(r.width, 250), vw - 24)),
      below = top + vh - r.bottom,
      above = r.top - top,
      down = below >= 170 || below >= above,
      calendar = popup.classList.contains("k-calendar"),
      maxHeight = Math.max(
        40,
        calendar
          ? vh - 24
          : Math.min(340, (down ? below : above) - 18, vh - 24),
      );
    popup.style.width = width + "px";
    popup.style.maxHeight = maxHeight + "px";
    popup.style.overflowY = "auto";
    const w = popup.offsetWidth || width,
      height = Math.min(
        popup.scrollHeight,
        popup.offsetHeight || maxHeight,
        maxHeight,
      );
    popup.style.left =
      Math.max(left + 12, Math.min(r.left, left + vw - w - 12)) + "px";
    let y = down ? r.bottom + 6 : r.top - height - 6;
    if (calendar && y + height > top + vh - 12)
      y = r.top - height - 6 >= top + 12 ? r.top - height - 6 : y;
    popup.style.top =
      Math.max(top + 12, Math.min(y, top + vh - height - 12)) + "px";
  }
  function open(owner, popup) {
    close();
    const container = owner.closest("dialog[open]") || document.body;
    if (popup.parentElement !== container) container.append(popup);
    active = { owner, popup };
    popup.hidden = false;
    if (popup.showPopover) popup.showPopover();
    owner.setAttribute("aria-expanded", "true");
    place();
  }
  function makePopup(cls) {
    const p = document.createElement("div");
    p.className = "k-picker " + cls;
    p.hidden = true;
    p.id = "k-picker-" + ++serial;
    if ("showPopover" in p) p.setAttribute("popover", "manual");
    document.body.append(p);
    return p;
  }
  function select(el) {
    const owner = button("", "k-select");
    owner.setAttribute("role", "combobox");
    owner.setAttribute("aria-haspopup", "listbox");
    owner.setAttribute("aria-expanded", "false");
    owner.setAttribute("aria-label", title(el));
    const popup = makePopup("k-options");
    popup.setAttribute("role", "listbox");
    popup.setAttribute("aria-label", title(el));
    owner.setAttribute("aria-controls", popup.id);
    if (el.multiple) popup.setAttribute("aria-multiselectable", "true");
    el.classList.add("k-native-select");
    el.setAttribute("aria-hidden", "true");
    el.tabIndex = -1;
    el.after(owner);
    el.kOwner = owner;
    let index = 0,
      typing = "",
      timer;
    function sync() {
      owner.textContent =
        [...el.selectedOptions].map((o) => o.textContent).join(", ") ||
        "Choose…";
      owner.disabled = el.disabled;
      owner.setAttribute("aria-required", String(el.required));
      owner.setAttribute(
        "aria-invalid",
        String(el.getAttribute("aria-invalid") === "true"),
      );
      if (el.getAttribute("aria-describedby"))
        owner.setAttribute(
          "aria-describedby",
          el.getAttribute("aria-describedby"),
        );
      popup.replaceChildren();
      const list = [...el.options];
      list.forEach((opt, i) => {
        const b = button(opt.textContent, "k-option");
        b.setAttribute("role", "option");
        b.setAttribute("aria-selected", String(opt.selected));
        b.disabled = el.disabled || opt.disabled || opt.parentElement.disabled;
        b.id = popup.id + "-" + i;
        b.tabIndex = -1;
        if (
          opt.parentElement.tagName === "OPTGROUP" &&
          opt === opt.parentElement.querySelector("option")
        ) {
          const h = document.createElement("div");
          h.className = "k-option-group";
          h.textContent = opt.parentElement.label;
          popup.append(h);
        }
        b.onclick = () => choose(i);
        popup.append(b);
      });
    }
    function focus(i) {
      const list = [...popup.querySelectorAll("[role=option]")];
      if (!list.length) return;
      index = Math.max(0, Math.min(i, list.length - 1));
      for (let n = 0; n < list.length && list[index].disabled; n++)
        index = (index + 1) % list.length;
      list.forEach((b, n) => b.classList.toggle("is-active", n === index));
      owner.setAttribute("aria-activedescendant", list[index].id);
      owner.focus({ preventScroll: true });
      list[index].scrollIntoView({ block: "nearest" });
    }
    function choose(i) {
      const opt = el.options[i];
      if (!opt || opt.disabled || opt.parentElement.disabled || el.disabled)
        return;
      if (el.multiple) opt.selected = !opt.selected;
      else el.selectedIndex = i;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      sync();
      if (el.multiple) focus(i);
      else close(true);
    }
    function show() {
      sync();
      open(owner, popup);
      focus(Math.max(0, el.selectedIndex));
    }
    owner.onclick = () => (active?.owner === owner ? close() : show());
    const keys = (e) => {
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
        e.preventDefault();
        if (active?.owner !== owner) show();
        else
          focus(
            e.key === "Home"
              ? 0
              : e.key === "End"
                ? el.options.length - 1
                : index + (e.key === "ArrowDown" ? 1 : -1),
          );
      } else if (
        (e.key === "Enter" || e.key === " ") &&
        active?.owner === owner
      ) {
        e.preventDefault();
        choose(index);
      } else if (
        e.key.length === 1 &&
        !e.ctrlKey &&
        !e.metaKey &&
        e.key !== " "
      ) {
        typing += e.key.toLowerCase();
        clearTimeout(timer);
        timer = setTimeout(() => (typing = ""), 600);
        const found = [...el.options].findIndex(
          (o) => !o.disabled && o.textContent.toLowerCase().startsWith(typing),
        );
        if (found >= 0) {
          e.preventDefault();
          if (active?.owner !== owner) show();
          focus(found);
        }
      }
    };
    owner.addEventListener("keydown", keys);
    popup.addEventListener("keydown", keys);
    el.addEventListener("change", sync);
    new MutationObserver(sync).observe(el, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: [
        "disabled",
        "selected",
        "label",
        "required",
        "aria-invalid",
        "aria-describedby",
      ],
    });
    el.form?.addEventListener("reset", () => setTimeout(sync, 0));
    syncers.set(el, sync);
    sync();
  }
  function number(el) {
    const wrap = document.createElement("span");
    wrap.className = "k-number";
    el.before(wrap);
    wrap.append(el);
    const minus = button("−", "k-step"),
      plus = button("+", "k-step");
    minus.setAttribute("aria-label", "Decrease " + title(el));
    plus.setAttribute("aria-label", "Increase " + title(el));
    wrap.append(minus, plus);
    const sync = () => {
      minus.disabled =
        el.disabled ||
        el.readOnly ||
        (el.value !== "" &&
          el.min !== "" &&
          Number(el.value) <= Number(el.min));
      plus.disabled =
        el.disabled ||
        el.readOnly ||
        (el.value !== "" &&
          el.max !== "" &&
          Number(el.value) >= Number(el.max));
    };
    let suppressClick = false;
    for (const [b, d] of [
      [minus, -1],
      [plus, 1],
    ]) {
      let holdTimer = 0,
        repeatTimer = 0;
      const stop = () => {
        clearTimeout(holdTimer);
        clearInterval(repeatTimer);
      };
      b.addEventListener("pointerdown", (e) => {
        if (e.button > 0 || b.disabled) return;
        stop();
        holdTimer = setTimeout(() => {
          suppressClick = true;
          repeatTimer = setInterval(() => {
            if (b.disabled) return stop();
            b.click();
          }, 70);
        }, 420);
      });
      for (const type of ["pointerup", "pointerleave", "pointercancel"])
        b.addEventListener(type, stop);
      b.addEventListener(
        "click",
        (e) => {
          if (suppressClick && e.detail > 0) {
            suppressClick = false;
            e.stopImmediatePropagation();
            e.preventDefault();
          }
        },
        true,
      );
      b.onclick = () => {
        if (!el.disabled && !el.readOnly) {
          if (el.step === "any") {
            const step = 1,
              value = Number(el.value) || 0;
            el.value = String(
              Math.min(
                el.max === "" ? Infinity : Number(el.max),
                Math.max(
                  el.min === "" ? -Infinity : Number(el.min),
                  value + d * step,
                ),
              ),
            );
          } else {
            try {
              d > 0 ? el.stepUp() : el.stepDown();
            } catch {
              return;
            }
          }
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
          sync();
        }
      };
    }
    el.addEventListener("input", sync);
    el.addEventListener("change", sync);
    new MutationObserver(sync).observe(el, {
      attributes: true,
      attributeFilter: ["disabled", "readonly", "min", "max", "step"],
    });
    el.form?.addEventListener("reset", () => setTimeout(sync, 0));
    syncers.set(el, sync);
    sync();
  }
  const pad = (x) => String(x).padStart(2, "0"),
    iso = (d) =>
      String(d.getFullYear()).padStart(4, "0") +
      "-" +
      pad(d.getMonth() + 1) +
      "-" +
      pad(d.getDate());
  function date(el) {
    const mode = el.type;
    el.type = "text";
    el.dataset.kDate = mode;
    el.placeholder =
      mode === "datetime-local" ? "YYYY-MM-DDTHH:mm" : "YYYY-MM-DD";
    el.setAttribute("inputmode", "numeric");
    el.setAttribute("autocomplete", "off");
    const withTime = mode === "datetime-local";
    const format = (digits) => {
      const d = digits.slice(0, withTime ? 12 : 8);
      let out = d.slice(0, 4);
      if (d.length > 4) out += "-" + d.slice(4, 6);
      if (d.length > 6) out += "-" + d.slice(6, 8);
      if (withTime && d.length > 8) out += "T" + d.slice(8, 10);
      if (withTime && d.length > 10) out += ":" + d.slice(10, 12);
      return out;
    };
    el.addEventListener("input", (event) => {
      if (event.inputType === "insertReplacementText") return;
      const raw = el.value,
        caret = el.selectionStart ?? raw.length;
      const before = raw.slice(0, caret).replace(/\D/g, "").length;
      const parts = raw.split(/\D+/);
      const digits =
        parts.length > 1
          ? parts
              .map((x, i) =>
                i > 0 && i < parts.length - 1 && x.length === 1 ? "0" + x : x,
              )
              .join("")
          : raw.replace(/\D/g, "");
      const formatted = format(digits);
      if (formatted === raw) return;
      el.value = formatted;
      let seen = 0,
        pos = 0;
      if (caret >= raw.length) pos = formatted.length;
      while (pos < formatted.length && seen < before && caret < raw.length) {
        if (/\d/.test(formatted[pos])) seen++;
        pos++;
      }
      el.setSelectionRange(pos, pos);
    });
    el.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
      const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?$/.exec(el.value);
      if (!m) return;
      event.preventDefault();
      const dir = event.key === "ArrowUp" ? 1 : -1,
        at = el.selectionStart ?? 0;
      const part = at <= 4 ? 0 : at <= 7 ? 1 : at <= 10 ? 2 : at <= 13 ? 3 : 4;
      const d = new Date(+m[1], +m[2] - 1, +m[3], +(m[4] ?? 9), +(m[5] ?? 0));
      if (part === 0) d.setFullYear(d.getFullYear() + dir);
      else if (part === 1) d.setMonth(d.getMonth() + dir);
      else if (part === 2) d.setDate(d.getDate() + dir);
      else if (part === 3 && withTime) d.setHours(d.getHours() + dir);
      else if (withTime) d.setMinutes(d.getMinutes() + dir);
      else d.setDate(d.getDate() + dir);
      el.value =
        iso(d) +
        (withTime ? "T" + pad(d.getHours()) + ":" + pad(d.getMinutes()) : "");
      const range = [
        [0, 4],
        [5, 7],
        [8, 10],
        [11, 13],
        [14, 16],
      ][part];
      el.setSelectionRange(range[0], range[1]);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    });
    const wrap = document.createElement("span");
    wrap.className = "k-date";
    el.before(wrap);
    wrap.append(el);
    const owner = button("", "k-calendar-toggle");
    owner.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5h14v16H5zM5 10h14M8 3v4m8-4v4"/></svg>';
    owner.setAttribute("aria-label", "Choose " + title(el));
    owner.setAttribute("aria-haspopup", "dialog");
    owner.setAttribute("aria-expanded", "false");
    wrap.append(owner);
    const popup = makePopup("k-calendar");
    popup.setAttribute("role", "dialog");
    popup.setAttribute("aria-label", "Choose " + title(el));
    owner.setAttribute("aria-controls", popup.id);
    let view = new Date(),
      pick = "days";
    const validationInput = document.createElement("input");
    validationInput.type = mode;
    function valid() {
      owner.disabled = el.disabled || el.readOnly;
      const value = el.value;
      if (!value) {
        el.setCustomValidity("");
        return;
      }
      // Preserve the browser's date, precision and step-base rules after the
      // visible field becomes text. Invalid constraints retain native semantics.
      validationInput.min = el.min;
      validationInput.max = el.max;
      validationInput.step = el.step;
      validationInput.setAttribute("value", el.getAttribute("value") || "");
      validationInput.value = value;
      const good =
        validationInput.value !== "" && validationInput.validity.valid;
      el.setCustomValidity(
        good
          ? ""
          : "Choose a valid " +
              (mode === "datetime-local" ? "date and time" : "date") +
              " within the allowed range.",
      );
    }
    function draw() {
      popup.replaceChildren();
      const header = document.createElement("div");
      header.className = "k-calendar-heading";
      const prev = button("‹", "k-calendar-nav"),
        next = button("›", "k-calendar-nav"),
        heading = document.createElement("strong");
      const year = view.getFullYear(),
        page = Math.floor(year / 12) * 12,
        titleText =
          pick === "years"
            ? page + " \u2013 " + (page + 11)
            : pick === "months"
              ? String(year)
              : view.toLocaleDateString(undefined, {
                  month: "long",
                  year: "numeric",
                });
      const titleButton = button(titleText, "k-calendar-title");
      titleButton.setAttribute(
        "aria-label",
        pick === "days"
          ? titleText + ", choose month or year"
          : titleText + ", go back",
      );
      titleButton.onclick = () => {
        pick =
          pick === "days" ? "months" : pick === "months" ? "years" : "days";
        draw();
        popup.querySelector(".k-calendar-title").focus();
      };
      heading.append(titleButton);
      heading.setAttribute("aria-live", "polite");
      const step = (dir) => {
        view.setDate(1);
        if (pick === "days") view.setMonth(view.getMonth() + dir);
        else if (pick === "months") view.setFullYear(year + dir);
        else view.setFullYear(year + dir * 12);
      };
      prev.setAttribute(
        "aria-label",
        pick === "days"
          ? "Previous month"
          : pick === "months"
            ? "Previous year"
            : "Previous years",
      );
      next.setAttribute(
        "aria-label",
        pick === "days"
          ? "Next month"
          : pick === "months"
            ? "Next year"
            : "Next years",
      );
      prev.onclick = () => {
        step(-1);
        draw();
        popup.querySelector(".k-calendar-nav").focus();
      };
      next.onclick = () => {
        step(1);
        draw();
        popup.querySelectorAll(".k-calendar-nav")[1].focus();
      };
      header.append(prev, heading, next);
      popup.append(header);
      if (pick !== "days") {
        const choices = document.createElement("div");
        choices.className = "k-calendar-choices";
        choices.setAttribute("role", "group");
        const minD = el.min ? el.min.slice(0, 10) : "",
          maxD = el.max ? el.max.slice(0, 10) : "";
        for (let i = 0; i < 12; i++) {
          const y = pick === "years" ? page + i : year,
            m = pick === "years" ? view.getMonth() : i,
            first = iso(new Date(y, m, 1)),
            last = iso(
              new Date(
                pick === "years" ? y + 1 : y,
                pick === "years" ? 0 : m + 1,
                0,
              ),
            ),
            b = button(
              pick === "years"
                ? String(y)
                : new Date(y, i, 1).toLocaleDateString(undefined, {
                    month: "short",
                  }),
              "k-calendar-choice",
            );
          b.setAttribute(
            "aria-pressed",
            String(pick === "years" ? y === year : i === view.getMonth()),
          );
          b.disabled = !!(
            (minD && last < minD) ||
            (maxD && (pick === "years" ? iso(new Date(y, 0, 1)) : first) > maxD)
          );
          b.onclick = () => {
            view.setDate(1);
            if (pick === "years") {
              view.setFullYear(y);
              pick = "months";
            } else {
              view.setMonth(i);
              pick = "days";
            }
            draw();
            popup.querySelector(".k-calendar-title").focus();
          };
          choices.append(b);
        }
        popup.append(choices);
        if (active && active.popup === popup) place();
        return;
      }
      const weekdays = document.createElement("div");
      weekdays.className = "k-calendar-week";
      for (const name of ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]) {
        const s = document.createElement("span");
        s.textContent = name;
        weekdays.append(s);
      }
      popup.append(weekdays);
      const grid = document.createElement("div");
      grid.className = "k-calendar-grid";
      grid.setAttribute("role", "group");
      grid.setAttribute("aria-label", heading.textContent);
      const first = new Date(view.getFullYear(), view.getMonth(), 1),
        days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
      for (let i = 0; i < first.getDay(); i++)
        grid.append(document.createElement("span"));
      for (let day = 1; day <= days; day++) {
        const d = new Date(view.getFullYear(), view.getMonth(), day),
          value = iso(d),
          b = button(String(day), "k-calendar-day");
        b.dataset.date = value;
        b.tabIndex =
          el.value.slice(0, 10) === value ||
          (!el.value && value === iso(new Date()))
            ? 0
            : -1;
        b.setAttribute(
          "aria-label",
          d.toLocaleDateString(undefined, { dateStyle: "full" }),
        );
        b.setAttribute("aria-pressed", String(el.value.slice(0, 10) === value));
        b.disabled = !!(
          (el.min && value < el.min.slice(0, 10)) ||
          (el.max && value > el.max.slice(0, 10))
        );
        b.onclick = () => {
          el.value =
            value +
            (mode === "datetime-local"
              ? "T" +
                (el.value.includes("T") ? el.value.split("T")[1] : "09:00")
              : "");
          valid();
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
          if (mode === "datetime-local") draw();
          else close(true);
        };
        grid.append(b);
      }
      if (!grid.querySelector('[tabindex="0"]:not(:disabled)'))
        grid
          .querySelector("button:not(:disabled)")
          ?.setAttribute("tabindex", "0");
      popup.append(grid);
      grid.addEventListener("keydown", (e) => {
        const b = e.target.closest("[data-date]");
        if (!b) return;
        const jump = {
          ArrowLeft: -1,
          ArrowRight: 1,
          ArrowUp: -7,
          ArrowDown: 7,
        }[e.key];
        if (jump) {
          e.preventDefault();
          const buttons = [...grid.querySelectorAll("button")],
            i = buttons.indexOf(b);
          let index = Math.max(0, Math.min(buttons.length - 1, i + jump));
          // Disabled dates cannot receive focus. Keep the current enabled tab stop
          // when the requested direction reaches the allowed range boundary.
          while (buttons[index]?.disabled) index += Math.sign(jump);
          const target = buttons[index];
          if (!target) return;
          buttons.forEach((x) => (x.tabIndex = x === target ? 0 : -1));
          target.focus();
        }
      });
      if (mode === "datetime-local") {
        const time = document.createElement("div");
        time.className = "k-calendar-time";
        const label = document.createElement("span");
        label.textContent = "Time";
        time.append(label);
        const current = el.value.split("T")[1] || "09:00";
        const fields = document.createElement("div");
        fields.className = "k-time-fields";
        const sep = document.createElement("span");
        sep.className = "k-time-sep";
        sep.textContent = ":";
        for (const [name, value, max] of [
          ["Hour", current.slice(0, 2), 23],
          ["Minute", current.slice(3, 5), 59],
        ]) {
          const box = document.createElement("label");
          box.textContent = name;
          const input = document.createElement("input");
          input.type = "number";
          input.min = "0";
          input.max = String(max);
          input.value = String(Number(value) || 0);
          input.setAttribute("aria-label", name);
          input.oninput = () => {
            const [h, m] = [...time.querySelectorAll("input")].map((x) =>
              pad(Math.max(0, Math.min(Number(x.max), Number(x.value) || 0))),
            );
            el.value = (el.value.slice(0, 10) || iso(view)) + "T" + h + ":" + m;
            valid();
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
          };
          box.append(input);
          fields.append(box);
          if (name === "Hour") fields.append(sep);
        }
        const presets = document.createElement("div");
        presets.className = "k-time-presets";
        for (const [text, h, m] of [
          ["Morning", 9, 0],
          ["Noon", 12, 0],
          ["Evening", 18, 0],
        ]) {
          const b = button(text);
          b.onclick = () => {
            const [hh, mm] = fields.querySelectorAll("input");
            hh.value = String(h);
            mm.value = String(m);
            mm.oninput();
          };
          presets.append(b);
        }
        time.append(fields, presets);
        popup.append(time);
        const done = button("Done", "k-calendar-done");
        done.onclick = () => close(true);
        popup.append(done);
      }
      const actions = document.createElement("div");
      actions.className = "k-calendar-actions";
      const today = button("Today"),
        clear = button("Clear");
      today.onclick = () => {
        view = new Date();
        el.value = iso(view) + (mode === "datetime-local" ? "T09:00" : "");
        valid();
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        draw();
      };
      clear.onclick = () => {
        el.value = "";
        valid();
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        close(true);
      };
      actions.append(today, clear);
      popup.append(actions);
      place();
    }
    owner.onclick = () => {
      if (el.disabled || el.readOnly) return;
      if (active?.owner === owner) return close();
      const date = new Date(
        (el.value.slice(0, 10) || iso(new Date())) + "T12:00:00",
      );
      view = Number.isNaN(date.getTime()) ? new Date() : date;
      view.setDate(1);
      pick = "days";
      draw();
      open(owner, popup);
      (
        popup.querySelector("[aria-pressed=true]") ||
        popup.querySelector(
          '[data-date="' + iso(new Date()) + '"]:not(:disabled)',
        ) ||
        popup.querySelector(".k-calendar-day:not(:disabled)")
      )?.focus();
    };
    el.addEventListener("input", valid);
    el.addEventListener("change", valid);
    el.form?.addEventListener("reset", () => setTimeout(valid, 0));
    new MutationObserver(valid).observe(el, {
      attributes: true,
      attributeFilter: ["disabled", "readonly", "min", "max", "step", "value"],
    });
    syncers.set(el, valid);
    valid();
  }
  const fieldContainer = (el) =>
    el.closest(".k-number,.k-date")?.parentElement || el.parentElement;
  function errors(el) {
    el.setAttribute("aria-invalid", "true");
    el.kOwner?.setAttribute("aria-invalid", "true");
    const container = fieldContainer(el);
    let hint = container.querySelector(":scope > .k-field-error");
    if (!hint) {
      hint = document.createElement("small");
      hint.className = "k-field-error";
      hint.setAttribute("role", "alert");
      container.append(hint);
    }
    hint.textContent = el.validationMessage;
  }
  function scan(root) {
    if (root.nodeType !== 1 && root !== document) return;
    const nodes = [
      ...(root.matches?.("select,input,textarea") ? [root] : []),
      ...root.querySelectorAll("select,input,textarea"),
    ];
    for (const el of nodes) {
      if (seen.has(el)) continue;
      seen.add(el);
      if (el.tagName === "SELECT") select(el);
      else if (el.type === "number") number(el);
      else if (["date", "datetime-local"].includes(el.type)) date(el);
      else if (el.type === "checkbox" && el.hasAttribute("data-core-switch"))
        el.setAttribute("role", "switch");
      el.addEventListener("invalid", (e) => {
        e.preventDefault();
        errors(el);
        if (el.kOwner) requestAnimationFrame(() => el.kOwner.focus());
      });
      el.addEventListener("input", () => {
        el.removeAttribute("aria-invalid");
        fieldContainer(el).querySelector(":scope > .k-field-error")?.remove();
      });
    }
    if (root.matches?.("form[data-kag-wizard]")) wizard(root);
    root.querySelectorAll?.("form[data-kag-wizard]").forEach(wizard);
  }
  function wizard(form) {
    if (wizards.has(form)) return;
    wizards.add(form);
    form.noValidate = true;
    const groups = JSON.parse(form.dataset.kagWizard),
      steps = [],
      progress = document.createElement("ol");
    progress.className = "k-wizard-progress";
    progress.setAttribute("aria-label", "Application steps");
    const submit = form.querySelector("button[type=submit]"),
      actions = document.createElement("div");
    actions.className = "k-wizard-actions";
    const back = button("Back", "button"),
      next = button("Continue →", "button primary");
    actions.append(back, next);
    form.prepend(progress);
    for (const group of groups) {
      const fieldset = document.createElement("fieldset");
      fieldset.className = "k-wizard-step";
      const legend = document.createElement("legend");
      legend.textContent = group.title;
      fieldset.append(legend);
      for (const name of group.fields) {
        const field = form.elements.namedItem(name);
        const node = field?.closest("label");
        if (node) fieldset.append(node);
      }
      form.insertBefore(fieldset, submit);
      steps.push(fieldset);
      const item = document.createElement("li");
      item.textContent = group.title;
      progress.append(item);
    }
    const review = document.createElement("fieldset");
    review.className = "k-wizard-step";
    review.innerHTML =
      '<legend>Review your application</legend><p>Check your answers before sending them to Team reviewers.</p><dl class="k-wizard-review"></dl>';
    form.insertBefore(review, submit);
    steps.push(review);
    const last = document.createElement("li");
    last.textContent = "Review";
    progress.append(last);
    actions.append(submit);
    form.append(actions);
    let current = 0;
    function show(i) {
      current = i;
      steps.forEach((step, n) => (step.hidden = n !== i));
      [...progress.children].forEach((item, n) => {
        item.setAttribute("aria-current", n === i ? "step" : "false");
        item.classList.toggle("complete", n < i);
      });
      back.hidden = i === 0;
      next.hidden = i === steps.length - 1;
      submit.hidden = i !== steps.length - 1;
      if (i === steps.length - 1) {
        const dl = review.querySelector("dl");
        dl.replaceChildren();
        for (const group of groups)
          for (const name of group.fields) {
            const field = form.elements.namedItem(name),
              dt = document.createElement("dt"),
              dd = document.createElement("dd");
            dt.textContent = title(field);
            dd.textContent = field.value || "Not provided";
            dl.append(dt, dd);
          }
      }
    }
    function check(step) {
      for (const field of step.querySelectorAll("input,select,textarea"))
        if (!field.checkValidity()) {
          errors(field);
          (field.kOwner || field).focus();
          return false;
        }
      return true;
    }
    next.onclick = () => {
      if (check(steps[current])) {
        show(current + 1);
        steps[current].querySelector("legend").tabIndex = -1;
        steps[current].querySelector("legend").focus();
      }
    };
    back.onclick = () => show(Math.max(0, current - 1));
    form.addEventListener(
      "submit",
      (e) => {
        for (let i = 0; i < steps.length - 1; i++)
          if (!check(steps[i])) {
            e.preventDefault();
            e.stopPropagation();
            show(i);
            (
              steps[i].querySelector("[aria-invalid=true]")?.kOwner ||
              steps[i].querySelector("[aria-invalid=true]")
            )?.focus();
            return;
          }
        if (current !== steps.length - 1) {
          e.preventDefault();
          e.stopPropagation();
          show(current + 1);
        }
      },
      true,
    );
    show(0);
  }
  document.addEventListener(
    "click",
    (e) => {
      if (
        active &&
        !active.owner.contains(e.target) &&
        !active.popup.contains(e.target)
      )
        close();
    },
    true,
  );
  document.addEventListener(
    "keydown",
    (e) => {
      if (!active) return;
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        close(true);
      } else if (e.key === "Tab") {
        if (active.popup.classList.contains("k-calendar")) {
          const fields = [
            ...active.popup.querySelectorAll(
              "button:not(:disabled),input:not(:disabled)",
            ),
          ].filter((x) => x.tabIndex >= 0);
          if (
            (e.shiftKey && document.activeElement === fields[0]) ||
            (!e.shiftKey && document.activeElement === fields.at(-1))
          )
            close(true);
        } else close(true);
      }
    },
    true,
  );
  window.visualViewport?.addEventListener("resize", place, { passive: true });
  window.visualViewport?.addEventListener("scroll", place, { passive: true });
  addEventListener("resize", place, { passive: true });
  addEventListener("scroll", place, { capture: true, passive: true });
  window.KagNodeControls = {
    core: true,
    enhance: () => scan(document),
    sync() {
      scan(document);
      document
        .querySelectorAll("input,select")
        .forEach((el) => syncers.get(el)?.());
    },
    close: () => close(),
  };
  scan(document);
  new MutationObserver((records) => {
    for (const record of records)
      for (const node of record.addedNodes) scan(node);
  }).observe(document.body, { childList: true, subtree: true });
})();
