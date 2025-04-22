// script.js

/* ---------- helper ---------- */
function setZoneState(zone, file /* File | null */) {
  const fileLabel = zone.querySelector(".file-label");
  const browseSection = zone.querySelector(".browse-section");
  const input = zone.querySelector("input");
  const removeBtn = zone.querySelector(".remove");

  if (file) {
    fileLabel.innerHTML = `<p>${file.name}</p>`;
    zone.classList.add("filled");
    input.disabled = true;
    removeBtn.classList.remove("hidden");
    browseSection.textContent = "";
    browseSection.style.backgroundColor = "#ff4d4d";
  } else {
    fileLabel.textContent =
      fileLabel.dataset.originalText ||
      (zone.id === "audioDrop" ? "Audio File" : "Lyrics File");
    zone.classList.remove("filled");
    input.disabled = false;
    removeBtn.classList.add("hidden");
    browseSection.textContent = "Browse";
    browseSection.style.backgroundColor = "#4294ff77";
  }
}

/* reset one zone */
function clearZone(zone) {
  const input = zone.querySelector("input");
  input.value = "";
  setZoneState(zone, null);
}

window.addEventListener("DOMContentLoaded", () => {
  ["audioDrop", "lyricsDrop"].forEach((id) => {
    const zone = document.getElementById(id);
    const input = zone.querySelector("input");
    const removeBtn = zone.querySelector(".remove");
    const fileLabel = zone.querySelector(".file-label");

    fileLabel.dataset.originalText = fileLabel.textContent;

    zone.addEventListener("dragover", (e) => {
      if (input.disabled) return;
      e.preventDefault();
      zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", () =>
      zone.classList.remove("dragover")
    );
    zone.addEventListener("drop", (e) => {
      if (input.disabled) return;
      e.preventDefault();
      zone.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        setZoneState(zone, input.files[0]);
      }
    });
    input.addEventListener("change", () =>
      setZoneState(zone, input.files[0] || null)
    );
    removeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      clearZone(zone);
    });
  });

  // upload & preview
  const form = document.getElementById("uploadForm");
  const preview = document.getElementById("preview");
  const player = videojs("player");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const audioFile = document.getElementById("audioFile").files[0];
    const lyricsFile = document.getElementById("lyricsFile").files[0];
    const videoName = document.getElementById("videoName").value.trim();

    if (!audioFile || !lyricsFile) {
      alert("Please select both audio and lyrics files");
      return;
    }

    const data = new FormData();
    data.append("audio", audioFile);
    data.append("lyrics", lyricsFile);
    data.append("videoName", videoName || "output");

    console.log("Audio File:", audioFile.name);
    console.log("Lyrics File:", lyricsFile.name);
    console.log("Video Name:", videoName || "output");

    const btn = document.getElementById("submitBtn");
    btn.disabled = true;
    btn.textContent = "Generating…";

    try {
      const res = await fetch("/generate", { method: "POST", body: data });
      if (!res.ok) throw new Error(await res.text());
      const { video_url, caption_url } = await res.json();

      player.src({ src: video_url, type: "video/mp4" });
      player.textTracks()[0].src = caption_url;
      preview.classList.remove("hidden");
      player.play();
    } catch (err) {
      alert(err.message || err);
    } finally {
      btn.disabled = false;
      btn.textContent = "Generate Video";
    }
  });
});
