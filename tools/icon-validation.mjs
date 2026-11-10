const allowedTags = new Set(["path", "rect", "circle", "ellipse"]);
const allowedAttributes = new Set([
  "d",
  "x",
  "y",
  "width",
  "height",
  "rx",
  "ry",
  "cx",
  "cy",
  "r",
]);
// A deliberately closed grammar. No arbitrary attributes, URLs, IDs, markup or code.
export function validateIcon(icon) {
  if (!/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/.test(icon.id))
    throw new Error(`Invalid ID: ${icon.id}`);
  if (!/^[a-z]+$/.test(icon.category))
    throw new Error(`Invalid category: ${icon.id}`);
  if (
    !icon.title ||
    !icon.tags.length ||
    icon.tags.some((t) => !/^[a-z0-9]+$/.test(t))
  )
    throw new Error(`Invalid metadata: ${icon.id}`);
  const elements = [
    ...icon.body.matchAll(/<([a-z]+)((?: [a-z]+="[^"]*")*)\/>/g),
  ];
  if (!elements.length || elements.map((m) => m[0]).join("") !== icon.body)
    throw new Error(`Invalid geometry: ${icon.id}`);
  for (const [, tag, attrs] of elements) {
    if (!allowedTags.has(tag)) throw new Error(`Unsafe element: ${icon.id}`);
    const present = new Set();
    for (const [, name, value] of attrs.matchAll(/ ([a-z]+)="([^"]*)"/g)) {
      if (!allowedAttributes.has(name) || present.has(name))
        throw new Error(`Unsafe attribute: ${icon.id}`);
      present.add(name);
      if (name === "d") {
        validatePath(value, icon.id);
        if (
          !/^[Mm][\d\s.,+\-AaCcHhLlMmQqSsTtVvZz]+$/.test(value) ||
          !/[\d]/.test(value)
        )
          throw new Error(`Invalid path: ${icon.id}`);
      } else if (
        !/^\d+(?:\.\d+)?$/.test(value) ||
        +value > 24 ||
        (["width", "height", "r", "rx", "ry"].includes(name) &&
          +value <= 0 &&
          name !== "rx")
      )
        throw new Error(`Invalid coordinate: ${icon.id}`);
    }
    const required = {
      path: ["d"],
      rect: ["x", "y", "width", "height"],
      circle: ["cx", "cy", "r"],
      ellipse: ["cx", "cy", "rx", "ry"],
    }[tag];
    if (required.some((a) => !present.has(a)))
      throw new Error(`Missing geometry attribute: ${icon.id}`);
  }
}

// Parse command arities as well as characters: malformed paths can silently vanish.
function validatePath(data, id) {
  const tokens =
    data.match(
      /[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g,
    ) || [];
  if (tokens.join("") !== data.replace(/[\s,]/g, ""))
    throw new Error(`Invalid path token: ${id}`);
  const arity = { m: 2, l: 2, h: 1, v: 1, c: 6, s: 4, q: 4, t: 2, a: 7, z: 0 };
  let index = 0;
  while (index < tokens.length) {
    const command = tokens[index++];
    if (!Object.hasOwn(arity, command.toLowerCase()))
      throw new Error(`Missing path command: ${id}`);
    const start = index;
    while (index < tokens.length && !/^[a-z]$/i.test(tokens[index])) index++;
    const values = tokens.slice(start, index).map(Number),
      count = arity[command.toLowerCase()];
    if (
      (count === 0 && values.length) ||
      (count > 0 && (!values.length || values.length % count))
    )
      throw new Error(`Path command arity: ${id} (${command})`);
    if (values.some((n) => !Number.isFinite(n) || Math.abs(n) > 100))
      throw new Error(`Path coordinate: ${id}`);
    if (command.toLowerCase() === "a")
      for (let n = 0; n < values.length; n += 7)
        if (
          values[n] < 0 ||
          values[n + 1] < 0 ||
          ![0, 1].includes(values[n + 3]) ||
          ![0, 1].includes(values[n + 4])
        )
          throw new Error(`Invalid arc: ${id}`);
  }
}
