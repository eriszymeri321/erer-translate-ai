const sourceLang = document.getElementById("sourceLang");
const targetLang = document.getElementById("targetLang");
const inputText = document.getElementById("inputText");
const outputText = document.getElementById("outputText");
const translateButton = document.getElementById("translateButton");
const swapButton = document.getElementById("swapButton");
const clearButton = document.getElementById("clearButton");
const copyButton = document.getElementById("copyButton");
const inputMeta = document.getElementById("inputMeta");
const statusText = document.getElementById("statusText");

// Serveri lokal Python që i përgjigjet kërkesave të përkthimit.
const isLocalDevServer =
  ["localhost", "127.0.0.1"].includes(window.location.hostname) &&
  window.location.port !== "8000";
const API_BASE_URL =
  window.__LINGUA_API_BASE__ ||
  (isLocalDevServer ? "http://127.0.0.1:8000" : window.location.origin);

const FALLBACK_TARGETS = {
  sq: "Shqip",
  en: "English",
  de: "Deutsch",
  fr: "Français",
  it: "Italiano",
  es: "Español",
  tr: "Türkçe",
  sr: "Srpski",
  el: "Ελληνικά",
};

function updateCharacterCount() {
  inputMeta.textContent = `${inputText.value.length} karaktere`;
}

// Ndryshon tekstin e statusit poshtë panelit të përkthimit.
function setStatus(message, type = "") {
  statusText.textContent = message;
  statusText.className = type ? type : "";
}

// Vendos përmbajtjen që shfaqet në panelin e rezultateve.
function setOutput(message) {
  outputText.textContent = message;
}

async function translateText() {
  // Merr tekstin nga fusha dhe e dërgon te backend-i për përkthim.
  const text = inputText.value.trim();
  if (!text) {
    setStatus("Shkruaj një tekst për ta përkthyer.", "error");
    setOutput("Përkthimi do të shfaqet këtu.");
    return;
  }

  translateButton.disabled = true;
  translateButton.textContent = "Duke përkthyer...";
  outputText.classList.add("loading");
  setStatus("Po përkthehet...", "");

  try {
    const response = await fetch(`${API_BASE_URL}/api/translate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        source: sourceLang.value,
        target: targetLang.value,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Përkthimi dështoi.");
    }

    setOutput(data.translated_text || "");
    const detected = data.detected_language
      ? ` (${data.detected_language_name || data.detected_language})`
      : "";
    setStatus(
      `Përkthyer nga ${data.source_name || "gjuha burimore"}${detected} në ${data.target_name || FALLBACK_TARGETS[targetLang.value] || targetLang.value}.`,
      "success",
    );
  } catch (error) {
    setOutput(
      "Nuk u arrit përkthimi. Kontrollo nëse serveri është duke punuar dhe nëse ka internet.",
    );
    setStatus(error.message, "error");
  } finally {
    translateButton.disabled = false;
    translateButton.textContent = "Përkthe tani";
    outputText.classList.remove("loading");
  }
}

async function copyTranslation() {
  // Kopjon tekstin e përkthyer në clipboard.
  const text = outputText.textContent.trim();
  if (!text || text === "Përkthimi do të shfaqet këtu.") {
    setStatus("Nuk ka tekst për kopjim.", "error");
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    setStatus("Përkthimi u kopjua.", "success");
  } catch {
    setStatus("Kopjimi nuk u lejua nga shfletuesi.", "error");
  }
}

function swapLanguages() {
  // Ndërron gjuhën burimore me atë të synuar.
  const currentSource = sourceLang.value;
  sourceLang.value = targetLang.value;
  targetLang.value = currentSource === "auto" ? "sq" : currentSource;
}

sourceLang.addEventListener("change", () => {
  if (sourceLang.value === targetLang.value) {
    targetLang.value = sourceLang.value === "auto" ? "en" : "sq";
  }
});

targetLang.addEventListener("change", () => {
  if (sourceLang.value !== "auto" && sourceLang.value === targetLang.value) {
    sourceLang.value = "auto";
  }
});

inputText.addEventListener("input", updateCharacterCount);
translateButton.addEventListener("click", translateText);
swapButton.addEventListener("click", swapLanguages);
clearButton.addEventListener("click", () => {
  inputText.value = "";
  updateCharacterCount();
  setOutput("Përkthimi do të shfaqet këtu.");
  setStatus("Gati për përkthim");
  inputText.focus();
});
copyButton.addEventListener("click", copyTranslation);

inputText.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    translateText();
  }
});

updateCharacterCount();
setOutput("Përkthimi do të shfaqet këtu.");
