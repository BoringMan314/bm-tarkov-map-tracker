const root = document.getElementById("embedded-root");
const viewport = document.getElementById("embedded-viewport");
const stage = document.getElementById("embedded-stage");
const content = document.getElementById("embedded-content");
const mapImage = document.getElementById("embedded-map");
const markersLayer = document.getElementById("embedded-markers");
const playerMarker = document.getElementById("embedded-player");
const playerImg = playerMarker?.querySelector("img");

let lastMapUrl = "";
let lastMarkersKey = "";
let pollTimer = null;

function formatCoord(value) {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return String(Math.round(value * 10) / 10);
}

function formatGameCoordLabel(gameX, gameZ) {
  return `${formatCoord(gameX)}, ${formatCoord(gameZ)}`;
}

function markerTransform(rotation) {
  const rot = Number(rotation) || 0;
  if (!rot) {
    return "translate(-50%, -50%)";
  }
  return `translate(-50%, -50%) rotate(${-rot}deg)`;
}

function renderMarkers(markers, view) {
  if (!markersLayer) {
    return;
  }
  const iw = Number(view.iw);
  const ih = Number(view.ih);
  if (!iw || !ih || !Array.isArray(markers)) {
    markersLayer.replaceChildren();
    lastMarkersKey = "";
    return;
  }

  const showNames = Boolean(view.showNames);
  const showCoords = Boolean(view.showCoords);
  const rotation = Number(view.rotation) || 0;
  const key = JSON.stringify({
    showNames,
    showCoords,
    rotation,
    markers,
  });
  if (key === lastMarkersKey) {
    return;
  }
  lastMarkersKey = key;

  const fragment = document.createDocumentFragment();
  for (const entry of markers) {
    const x = Number(entry.x);
    const y = Number(entry.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      continue;
    }
    const marker = document.createElement("div");
    marker.className = "exfil-marker";
    if (entry.kind) {
      marker.dataset.exfil = entry.kind;
    }
    marker.style.left = `${(x / iw) * 100}%`;
    marker.style.top = `${(y / ih) * 100}%`;
    marker.style.zIndex = String(Number(entry.zIndex) || 0);
    marker.style.transform = markerTransform(rotation);

    const icon = entry.icon ? String(entry.icon) : "exfil-pmc";
    const img = document.createElement("img");
    img.src = `/api/points/icons/${icon}.png`;
    img.alt = entry.name || entry.kind || "marker";
    img.draggable = false;
    marker.appendChild(img);

    const name = entry.name ? String(entry.name).trim() : "";
    if (name && showNames) {
      const labelEl = document.createElement("span");
      labelEl.className = "exfil-marker-label";
      labelEl.textContent = name;
      if (entry.color) {
        labelEl.style.color = entry.color;
      }
      marker.appendChild(labelEl);
    }

    const gameX = Number(entry.gameX);
    const gameZ = Number(entry.gameZ);
    if (showCoords && Number.isFinite(gameX) && Number.isFinite(gameZ)) {
      const coordsEl = document.createElement("span");
      coordsEl.className = "marker-coords-label";
      coordsEl.textContent = formatGameCoordLabel(gameX, gameZ);
      if (entry.color) {
        coordsEl.style.color = entry.color;
      }
      marker.appendChild(coordsEl);
    }

    fragment.appendChild(marker);
  }
  markersLayer.replaceChildren(fragment);
}

function renderPlayer(player, view) {
  if (!playerMarker) {
    return;
  }
  const iw = Number(view.iw);
  const ih = Number(view.ih);
  if (!view.showPlayer || !player || !iw || !ih) {
    playerMarker.classList.add("hidden");
    playerMarker.setAttribute("aria-hidden", "true");
    return;
  }

  const x = Number(player.x);
  const y = Number(player.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    playerMarker.classList.add("hidden");
    playerMarker.setAttribute("aria-hidden", "true");
    return;
  }

  playerMarker.classList.remove("hidden");
  playerMarker.setAttribute("aria-hidden", "false");
  playerMarker.style.left = `${(x / iw) * 100}%`;
  playerMarker.style.top = `${(y / ih) * 100}%`;
  playerMarker.style.transform = markerTransform(view.rotation);

  const imgRot = Number(player.imgRot);
  if (playerImg) {
    playerImg.style.transform = Number.isFinite(imgRot) ? `rotate(${imgRot}deg)` : "";
  }

  let coordsEl = playerMarker.querySelector(".marker-coords-label");
  const gameX = Number(player.gameX);
  const gameZ = Number(player.gameZ);
  if (view.showCoords && Number.isFinite(gameX) && Number.isFinite(gameZ)) {
    if (!coordsEl) {
      coordsEl = document.createElement("span");
      coordsEl.className = "marker-coords-label";
      playerMarker.appendChild(coordsEl);
    }
    coordsEl.textContent = formatGameCoordLabel(gameX, gameZ);
  } else if (coordsEl) {
    coordsEl.remove();
  }
}

function applyState(data) {
  if (!data?.active) {
    root.classList.add("is-idle");
    return;
  }
  root.classList.remove("is-idle");

  const size = Number(data.settings?.size) || 300;
  const opacity = Number(data.settings?.opacity) || 0;
  const alpha = Math.max(0, Math.min(1, 1 - opacity / 100));
  root.style.width = `${size}px`;
  root.style.height = `${size}px`;
  root.style.setProperty("--embedded-ui-scale", String(size / 300));
  viewport.style.opacity = String(alpha);
  viewport.style.borderColor = `rgba(51, 181, 229, ${0.45 * alpha})`;

  const view = data.viewport;
  if (!view || !view.iw || !view.ih) {
    if (markersLayer) {
      markersLayer.replaceChildren();
    }
    if (playerMarker) {
      playerMarker.classList.add("hidden");
    }
    return;
  }

  const scale = Number(view.scale) || 1;
  const tx = Number(view.tx) || 0;
  const ty = Number(view.ty) || 0;
  const rot = Number(view.rotation) || 0;
  const iw = Number(view.iw);
  const ih = Number(view.ih);

  content.style.width = `${iw * scale}px`;
  content.style.height = `${ih * scale}px`;
  content.style.transform = rot ? `rotate(${rot}deg)` : "";
  stage.style.transform = `translate(calc(-50% + ${tx}px), calc(-50% + ${ty}px))`;

  if (view.mapUrl && view.mapUrl !== lastMapUrl) {
    lastMapUrl = view.mapUrl;
    lastMarkersKey = "";
    mapImage.src = view.mapUrl;
  }

  renderMarkers(view.markers, view);
  renderPlayer(view.player, view);
}

async function pollState() {
  try {
    const res = await fetch("/api/embedded/state", { cache: "no-store" });
    if (!res.ok) {
      return;
    }
    applyState(await res.json());
  } catch {
  }
}

function startPolling() {
  pollState();
  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
  pollTimer = window.setInterval(pollState, 120);
}

startPolling();
