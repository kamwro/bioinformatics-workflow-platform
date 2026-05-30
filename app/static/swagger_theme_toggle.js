// bioflowops-theme-toggle : light/dark switch for Swagger UI (/docs).
// Enables or disables the dark override stylesheet and remembers the choice in
// localStorage. With no saved choice it follows the OS color scheme.
(function () {
  var STORAGE_KEY = "bioqc-swagger-theme";
  var style = document.getElementById("swagger-dark-style");
  var button = null;

  function preferred() {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "dark" || saved === "light") {
      return saved;
    }
    var prefersDark =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "dark" : "light";
  }

  function apply(theme) {
    if (style) {
      style.disabled = theme !== "dark";
    }
    if (button) {
      button.textContent = theme === "dark" ? "☀" : "☾";
      button.title =
        "Switch to " + (theme === "dark" ? "light" : "dark") + " mode";
    }
  }

  // Apply immediately during head parsing to avoid a flash of the wrong theme.
  apply(preferred());

  document.addEventListener("DOMContentLoaded", function () {
    button = document.createElement("button");
    button.id = "swagger-theme-toggle";
    button.type = "button";
    button.setAttribute("aria-label", "Toggle color theme");
    document.body.appendChild(button);

    button.addEventListener("click", function () {
      var next = preferred() === "dark" ? "light" : "dark";
      localStorage.setItem(STORAGE_KEY, next);
      apply(next);
    });

    apply(preferred());
  });
})();
