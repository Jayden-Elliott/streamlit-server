window.addEventListener("DOMContentLoaded", () => {
    let getCSSLink = (name) => {
        let link = document.createElement("link");
        link.type = "text/css";
        link.rel = "stylesheet";
        link.href = `/static/styles/${name}.css`;
        return link;
    }

    let loadColorScheme = (scheme) => {
        let head = document.querySelector("head");
        head.appendChild(getCSSLink(scheme));
        head.appendChild(getCSSLink("general"));
    }

    const colorScheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    loadColorScheme(colorScheme);

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e => {
        const colorScheme = e.matches ? "dark" : "light";
        loadColorScheme(colorScheme);
    });
});