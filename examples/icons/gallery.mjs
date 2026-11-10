const search = document.querySelector("#search"),
  category = document.querySelector("#category"),
  grid = document.querySelector("#grid"),
  count = document.querySelector("#count");
const appearance = document.querySelector("#appearance");
appearance.addEventListener(
  "change",
  () => (document.documentElement.dataset.appearance = appearance.value),
);
try {
  const response = await fetch("./catalog.json");
  if (!response.ok) throw new Error("Catalog unavailable");
  const { icons } = await response.json();
  for (const name of [...new Set(icons.map((i) => i.category))]) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name[0].toUpperCase() + name.slice(1);
    category.append(option);
  }
  let timer;
  function render() {
    const term = search.value.trim().toLowerCase();
    const matches = icons.filter(
      (i) =>
        (!category.value || i.category === category.value) &&
        (!term ||
          [i.id, i.title, i.category, ...i.tags]
            .join(" ")
            .toLowerCase()
            .includes(term)),
    );
    const fragment = document.createDocumentFragment();
    for (const icon of matches) {
      const card = document.createElement("article");
      card.className = "card";
      const samples = document.createElement("div");
      samples.className = "samples";
      samples.setAttribute("aria-hidden", "true");
      for (const size of [16, 20, 24]) {
        const sample = document.createElement("div");
        const image = document.createElement("img");
        image.src = icon.svg;
        image.width = size;
        image.height = size;
        image.alt = "";
        image.loading = "lazy";
        image.decoding = "async";
        const label = document.createElement("span");
        label.textContent = String(size);
        sample.append(image, label);
        samples.append(sample);
      }
      const heading = document.createElement("h2");
      heading.textContent = icon.id;
      const tag = document.createElement("p");
      tag.className = "category";
      tag.textContent = icon.category;
      const download = document.createElement("a");
      download.href = icon.svg;
      download.download = `${icon.id}.svg`;
      download.textContent = "Download SVG";
      download.setAttribute("aria-label", `Download ${icon.title} SVG`);
      card.append(samples, heading, tag, download);
      fragment.append(card);
    }
    grid.replaceChildren(fragment);
    count.textContent = `${matches.length} of ${icons.length} icons`;
    document.querySelector("#empty").hidden = matches.length > 0;
  }
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(render, 100);
  });
  category.addEventListener("change", render);
  render();
} catch {
  count.textContent =
    "Unable to load the catalog. Serve this folder from a local HTTP server and reload.";
}
