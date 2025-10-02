const API_BASE = "https://your-backend.onrender.com"; // replace with your Render backend URL

const urlInput = document.getElementById("url");
const modeSelect = document.getElementById("mode");
const resolutionContainer = document.getElementById("resolution-container");
const resolutionSelect = document.getElementById("resolution");
const fetchBtn = document.getElementById("fetch-info");
const downloadBtn = document.getElementById("download");
const statusText = document.getElementById("status");

modeSelect.addEventListener("change", () => {
  if (modeSelect.value === "resolution") {
    resolutionContainer.classList.remove("hidden");
  } else {
    resolutionContainer.classList.add("hidden");
  }
});

// Fetch video info
fetchBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  if (!url) return alert("Please enter a YouTube URL");

  statusText.textContent = "Fetching video info...";
  try {
    const res = await fetch(`${API_BASE}/info`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    statusText.textContent = `Title: ${data.title}`;

    // Populate resolutions
    resolutionSelect.innerHTML = "";
    data.resolutions.forEach(r => {
      const opt = document.createElement("option");
      opt.value = r;
      opt.textContent = `${r}p`;
      resolutionSelect.appendChild(opt);
    });

    downloadBtn.disabled = false;
  } catch (err) {
    statusText.textContent = "Error: " + err.message;
    downloadBtn.disabled = true;
  }
});

// Download
downloadBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  const mode = modeSelect.value;
  const height = resolutionSelect.value;

  statusText.textContent = "Downloading...";

  try {
    const res = await fetch(`${API_BASE}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, mode, height })
    });

    if (!res.ok) throw new Error("Download failed");

    // Convert response to file
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "video";
    a.click();

    statusText.textContent = "✅ Download complete!";
  } catch (err) {
    statusText.textContent = "Error: " + err.message;
  }
});