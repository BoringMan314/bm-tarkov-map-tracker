const STORAGE_KEY = "bm-tarkov-map-tracker.currentMap";
const POINT_SOURCE_KEY = "bm-tarkov-map-tracker.pointSource";
const DEFAULT_MAP = "woods";

const POINT_SOURCES = [
  { id: "tarkovdev_a", labelKey: "point_source_tarkovdev_a", fallback: "tarkov.dev_A" },
  { id: "tarkovdev_b", labelKey: "point_source_tarkovdev_b", fallback: "tarkov.dev_B" },
  { id: "eftarkov", labelKey: "point_source_eftarkov", fallback: "eftarkov.com" },
];

function normalizeStoredPointSource(raw) {
  if (raw === "tarkovdev" || raw === "tarkovdev_a") {
    return "tarkovdev_a";
  }
  if (raw === "eftarkov_a" || raw === "eftarkov_b") {
    return "eftarkov";
  }
  if (POINT_SOURCES.some((s) => s.id === raw)) {
    return raw;
  }
  return "tarkovdev_a";
}

function isDevPointSource(source = state.pointSource) {
  return source === "tarkovdev" || source === "tarkovdev_a" || source === "tarkovdev_b";
}

function isEftarkovPointSource(source = state.pointSource) {
  return source === "eftarkov";
}

function devMapVariant(source = state.pointSource) {
  return source === "tarkovdev_b" ? "B" : "A";
}

function pointsApiSource(source = state.pointSource) {
  if (isDevPointSource(source)) {
    return "tarkovdev";
  }
  if (isEftarkovPointSource(source)) {
    return "eftarkov";
  }
  return source;
}

const EXFIL_LAYER_Z = {
  pmc: 4,
  scav: 3,
  coop: 2,
  transit: 1,
};

const EXFIL_KINDS = [
  { kind: "pmc", labelKey: "marker_exfil_pmc", fallback: "PMC", icon: "exfil-pmc", color: "#00a700" },
  { kind: "scav", labelKey: "marker_exfil_scav", fallback: "Scav", icon: "exfil-scav", color: "#ca8a00" },
  { kind: "coop", labelKey: "marker_exfil_coop", fallback: "共用撤離點", icon: "exfil-coop", color: "#0292c0" },
  { kind: "transit", labelKey: "marker_exfil_transit", fallback: "轉移點", icon: "exfil-transit", color: "#cd1e2f" },
];

const state = {
  maps: [],
  currentId: DEFAULT_MAP,
  scale: 1,
  baseScale: 1,
  tx: 0,
  ty: 0,
  mapWidth: 0,
  mapHeight: 0,
  mapLoadToken: 0,
  overlayGeneration: 0,
  viewFitKey: "",
  dragging: false,
  dragStartX: 0,
  dragStartY: 0,
  panStartX: 0,
  panStartY: 0,
  locale: {
    code: "zh_TW",
    order: [],
    labels: {},
    strings: {},
    mapNames: {},
    exfilNames: {},
  },
  mapMeta: null,
  mapMetaBySource: {},
  exfilData: null,
  exfilDataBySource: {},
  tarkovDevMeta: null,
  tarkovDevMetaB: null,
  playerLocation: null,
  eftarkovMeta: null,
  pointSource: normalizeStoredPointSource(localStorage.getItem(POINT_SOURCE_KEY)),
  exfilFilters: {
    pmc: true,
    scav: true,
    transit: true,
    coop: true,
  },
  exfilShowNames: true,
  showMarkerCoords: false,
  showPlayer: true,
  playerCenterLock: false,
  embeddedPosition: "none",
  embeddedRange: 10,
  embeddedSize: 300,
  embeddedOffsetX: 250,
  embeddedOffsetY: 0,
  embeddedOpacity: 50,
  embeddedDisplayTarget: "none",
  catalogDefaultMap: DEFAULT_MAP,
  catalogError: false,
};

const viewport = document.getElementById("map-viewport");
const stage = document.getElementById("map-stage");
const mapContent = document.getElementById("map-content");
const mapInline = document.getElementById("map-inline");
const mapImage = document.getElementById("map-image");
const selectRoot = document.getElementById("map-select");
const selectBtn = document.getElementById("map-select-btn");
const dropdown = document.getElementById("map-dropdown");
const pointsSelectRoot = document.getElementById("points-select");
const pointsSelectBtn = document.getElementById("points-select-btn");
const pointsSelectLabel = document.getElementById("points-select-label");
const pointsPanel = document.getElementById("points-panel");
const resetBtn = document.getElementById("reset-view-btn");
const langSelectRoot = document.getElementById("lang-select");
const langSelectBtn = document.getElementById("lang-select-btn");
const langSelectLabel = document.getElementById("lang-select-label");
const langDropdown = document.getElementById("lang-dropdown");
const pointSourceBtn = document.getElementById("point-source-btn");
const pointSourceLabel = document.getElementById("point-source-label");
const resetViewLabel = document.getElementById("reset-view-label");
const mouseCoordX = document.getElementById("mouse-coord-x");
const mouseCoordY = document.getElementById("mouse-coord-y");
const exfilOverlay = document.getElementById("map-exfil-overlay");
const playerOverlay = document.getElementById("map-player-overlay");
const exfilFilterLabels = {
  group: document.getElementById("exfil-filter-group-label"),
  pmc: document.getElementById("exfil-filter-pmc-label"),
  scav: document.getElementById("exfil-filter-scav-label"),
  transit: document.getElementById("exfil-filter-transit-label"),
  coop: document.getElementById("exfil-filter-coop-label"),
  pmcNames: document.getElementById("exfil-filter-pmc-names-label"),
  showCoords: document.getElementById("exfil-filter-show-coords-label"),
  player: document.getElementById("exfil-filter-player-label"),
  playerLock: document.getElementById("exfil-filter-player-lock-label"),
};
const exfilGroupToggle = document.getElementById("exfil-filter-group");
const exfilCoopRow = document.getElementById("exfil-filter-coop-row");
const exfilPmcNamesToggle = document.getElementById("exfil-filter-pmc-names");
const exfilShowCoordsToggle = document.getElementById("exfil-filter-show-coords");
const exfilPlayerToggle = document.getElementById("exfil-filter-player");
const exfilPlayerLockToggle = document.getElementById("exfil-filter-player-lock");
const embeddedSelectRoot = document.getElementById("embedded-select");
const embeddedSelectBtn = document.getElementById("embedded-select-btn");
const embeddedSelectLabel = document.getElementById("embedded-select-label");
const embeddedPanel = document.getElementById("embedded-panel");
const embeddedPositionSelect = document.getElementById("embedded-position");
const embeddedRangeSelect = document.getElementById("embedded-range");
const embeddedSizeSelect = document.getElementById("embedded-size");
const embeddedOffsetXSelect = document.getElementById("embedded-offset-x");
const embeddedOffsetYSelect = document.getElementById("embedded-offset-y");
const embeddedOpacitySelect = document.getElementById("embedded-opacity");
const embeddedDisplayTargetLabel = document.getElementById("embedded-display-target-label");
const embeddedDisplayTargetValue = document.getElementById("embedded-display-target-value");
const embeddedFilterLabels = {
  panel: embeddedSelectLabel,
  displayTarget: embeddedDisplayTargetLabel,
  position: document.getElementById("embedded-position-label"),
  range: document.getElementById("embedded-range-label"),
  size: document.getElementById("embedded-size-label"),
  offsetX: document.getElementById("embedded-offset-x-label"),
  offsetY: document.getElementById("embedded-offset-y-label"),
  opacity: document.getElementById("embedded-opacity-label"),
};

function t(key, fallback = "") {
  return state.locale.strings[key] || fallback;
}

function mapLabel(id, fallback = id) {
  if (state.locale.mapNames && state.locale.mapNames[id]) {
    return state.locale.mapNames[id];
  }
  return t(`map_${id}`, fallback);
}

function exfilLabel(id, fallback = "") {
  if (id && state.locale.exfilNames && state.locale.exfilNames[id]) {
    return state.locale.exfilNames[id];
  }
  return fallback;
}

function currentLangLabel() {
  const code = state.locale.code;
  if (code && state.locale.labels && state.locale.labels[code]) {
    return state.locale.labels[code];
  }
  return t("language_name", "繁體中文");
}

function currentPointSourceLabel() {
  const entry = POINT_SOURCES.find((s) => s.id === state.pointSource) || POINT_SOURCES[0];
  return t(entry.labelKey, entry.fallback);
}

function refreshPointSourceLabel() {
  if (pointSourceLabel) {
    pointSourceLabel.textContent = currentPointSourceLabel();
  }
}

function applyLocale(payload) {
  if (!payload) {
    return;
  }
  state.locale.code = payload.locale || state.locale.code;
  state.locale.order = payload.order || state.locale.order;
  state.locale.labels = payload.labels || state.locale.labels;
  state.locale.strings = payload.strings || state.locale.strings;
  state.locale.mapNames = payload.mapNames || state.locale.mapNames;
  state.locale.exfilNames = payload.exfilNames || state.locale.exfilNames;
  if (resetViewLabel) {
    resetViewLabel.textContent = t("reset_view", "RESET VIEW");
  }
  if (langSelectLabel) {
    langSelectLabel.textContent = currentLangLabel();
  }
  document.title = t("project_name", document.title);
  refreshMapLabels();
  refreshExfilFilterLabels();
  refreshEmbeddedLabels();
  refreshPointOverlays();
  renderLangDropdown();
  refreshPointSourceLabel();
}

async function loadLocale() {
  const res = await fetch("/api/locale");
  if (!res.ok) {
    return;
  }
  applyLocale(await res.json());
}

async function setLocale(code) {
  const res = await fetch("/api/locale/set", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ locale: code }),
  });
  if (!res.ok) {
    return;
  }
  const payload = await res.json();
  applyLocale(payload);
  try {
    await reloadMapCatalog();
  } catch {
    setSelectErrorLabel();
  }
}

const mapContentCache = new Map();
const RASTER_MAX_DIMENSION = 7680;
const COM_RASTER_MAX_DIMENSION = 7680;

function clearMapContentCache() {
  for (const cached of mapContentCache.values()) {
    if (cached?.kind === "raster" || cached?.kind === "rasterOverlay") {
      revokeRasterCacheUrl(cached);
    }
  }
  mapContentCache.clear();
}

async function waitForImageElement(img) {
  if (img.complete && img.naturalWidth > 0) {
    return;
  }
  await new Promise((resolve, reject) => {
    const cleanup = () => {
      img.removeEventListener("load", onLoad);
      img.removeEventListener("error", onErr);
    };
    const onLoad = () => {
      cleanup();
      resolve();
    };
    const onErr = () => {
      cleanup();
      reject(new Error("map-img"));
    };
    img.addEventListener("load", onLoad);
    img.addEventListener("error", onErr);
  });
}

async function awaitMapImageReady(img) {
  try {
    if (typeof img.decode === "function") {
      await img.decode();
      if (img.naturalWidth > 0) {
        return;
      }
    }
  } catch {
  }
  await waitForImageElement(img);
}

async function prepareRasterDisplayUrl(blob, maxDimension = RASTER_MAX_DIMENSION) {
  const objectUrl = URL.createObjectURL(blob);
  const probe = new Image();
  try {
    await new Promise((resolve, reject) => {
      probe.onload = () => resolve();
      probe.onerror = () => reject(new Error("raster-probe"));
      probe.src = objectUrl;
    });
  } catch {
    URL.revokeObjectURL(objectUrl);
    throw new Error("raster-probe");
  }
  const nw = probe.naturalWidth || 0;
  const nh = probe.naturalHeight || 0;
  const maxEdge = Math.max(nw, nh);
  if (!nw || !nh || maxEdge <= maxDimension) {
    return objectUrl;
  }
  URL.revokeObjectURL(objectUrl);

  if (typeof createImageBitmap === "function") {
    try {
      const scale = maxDimension / maxEdge;
      const rw = Math.max(1, Math.round(nw * scale));
      const rh = Math.max(1, Math.round(nh * scale));
      const resized = await createImageBitmap(blob, {
        resizeWidth: rw,
        resizeHeight: rh,
        resizeQuality: "high",
      });
      const canvas = document.createElement("canvas");
      canvas.width = rw;
      canvas.height = rh;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        resized.close();
        throw new Error("raster-canvas");
      }
      ctx.drawImage(resized, 0, 0);
      resized.close();
      const outBlob = await new Promise((resolve, reject) => {
        canvas.toBlob(
          (value) => (value ? resolve(value) : reject(new Error("raster-blob"))),
          "image/png"
        );
      });
      return URL.createObjectURL(outBlob);
    } catch {
    }
  }

  const scale = maxDimension / maxEdge;
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(nw * scale));
  canvas.height = Math.max(1, Math.round(nh * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("raster-canvas");
  }
  ctx.drawImage(probe, 0, 0, canvas.width, canvas.height);
  const outBlob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      (value) => (value ? resolve(value) : reject(new Error("raster-blob"))),
      "image/png"
    );
  });
  return URL.createObjectURL(outBlob);
}

async function prepareMapDisplayBlob(blob) {
  const maxDim = isEftarkovPointSource() ? COM_RASTER_MAX_DIMENSION : RASTER_MAX_DIMENSION;
  try {
    return await prepareRasterDisplayUrl(blob, maxDim);
  } catch {
    return URL.createObjectURL(blob);
  }
}

async function resolveRasterDisplaySrc(fetchUrl, blob) {
  const maxDim = isEftarkovPointSource() ? COM_RASTER_MAX_DIMENSION : RASTER_MAX_DIMENSION;
  const objectUrl = URL.createObjectURL(blob);
  const probe = new Image();
  try {
    await new Promise((resolve, reject) => {
      probe.onload = () => resolve();
      probe.onerror = () => reject(new Error("raster-probe"));
      probe.src = objectUrl;
    });
  } catch {
    URL.revokeObjectURL(objectUrl);
    const blobUrl = await prepareMapDisplayBlob(blob);
    return { imageSrc: blobUrl, blobUrl };
  }
  const maxEdge = Math.max(probe.naturalWidth || 0, probe.naturalHeight || 0);
  URL.revokeObjectURL(objectUrl);
  if (!maxEdge || maxEdge <= maxDim) {
    return { imageSrc: fetchUrl, blobUrl: null };
  }
  const blobUrl = await prepareMapDisplayBlob(blob);
  return { imageSrc: blobUrl, blobUrl };
}

function revokeRasterCacheUrl(cached) {
  if (cached?.blobUrl) {
    URL.revokeObjectURL(cached.blobUrl);
  }
}

function rasterMaxDisplayDimension() {
  return isEftarkovPointSource() ? COM_RASTER_MAX_DIMENSION : RASTER_MAX_DIMENSION;
}

function rasterMetaMaxEdge(mapId = state.currentId, entry = null) {
  const meta = devDisplayMeta(mapId) || state.mapMeta?.[mapId];
  const e = entry || state.maps.find((m) => m.id === mapId);
  const mw = Number(meta?.width) || Number(e?.width) || 0;
  const mh = Number(meta?.height) || Number(e?.height) || 0;
  return Math.max(mw, mh);
}

function canLoadRasterDirect(mapId = state.currentId, entry = null) {
  if (usesSatelliteOverlay(mapId)) {
    return false;
  }
  const edge = rasterMetaMaxEdge(mapId, entry);
  return edge > 0 && edge <= rasterMaxDisplayDimension();
}

async function loadRasterImageSoft(img) {
  try {
    await awaitMapImageReady(img);
    return;
  } catch {
  }
  for (let i = 0; i < 20; i += 1) {
    if (img.naturalWidth > 0 && img.naturalHeight > 0) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  if (!img.naturalWidth || !img.naturalHeight) {
    throw new Error("map-img");
  }
}

function isRasterMapContentType(contentType) {
  const ct = (contentType || "").split(";")[0].trim().toLowerCase();
  return ct.startsWith("image/") && !ct.includes("svg");
}

const MAP_MIN_ZOOM_RATIO = {
  reserve: 1.3,
  labs: 0.9,
  labyrinth: 0.9,
};

const COM_MAP_MIN_ZOOM_RATIO = {
  reserve: 0.72,
  streets: 0.82,
  shoreline: 0.85,
};

function displayRotationForMap(mapId = state.currentId) {
  const meta = state.mapMeta?.[mapId];
  const fromMeta = Number(meta?.display_rotation);
  if (Number.isFinite(fromMeta) && fromMeta !== 0) {
    return fromMeta;
  }
  return 0;
}

const DEFAULT_EXFIL_MARKER_ROTATION = 180;
const EXFIL_MARKER_ROTATION_DEG = {
  factory: 0,
  labs: 0,
  labyrinth: 0,
};

function exfilMarkerRotationDegrees(mapId = state.currentId) {
  if (Object.prototype.hasOwnProperty.call(EXFIL_MARKER_ROTATION_DEG, mapId)) {
    return EXFIL_MARKER_ROTATION_DEG[mapId];
  }
  return DEFAULT_EXFIL_MARKER_ROTATION;
}

function rotateMapPixels(x, y, mapW, mapH, degrees) {
  if (!degrees) {
    return { x, y };
  }
  const cx = mapW / 2;
  const cy = mapH / 2;
  const rad = (degrees * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const dx = x - cx;
  const dy = y - cy;
  return {
    x: cx + dx * cos + dy * sin,
    y: cy - dx * sin + dy * cos,
  };
}

const RASTER_TILE_MAPS = new Set(["factory", "labs", "labyrinth"]);

const DEFAULT_DEV_COORD_PROFILE = { pointMeta: "self", coordMode: "schematic", flipY: false, flipX: false };

const MAP_COORD_PROFILES = {
  factory: {
    dev_a: { pointMeta: "a", coordMode: "raster_crop" },
    dev_b: { pointMeta: "a", coordMode: "raster_crop", sizeMeta: "b", scaleCoordsFromDevA: true },
  },
  customs: {
    dev_a: { pointMeta: "a", coordMode: "raster_crop", flipX: true },
    dev_b: { pointMeta: "b", coordMode: "schematic" },
  },
  interchange: {
    dev_a: { pointMeta: "a", coordMode: "raster_crop", flipX: true },
    dev_b: { pointMeta: "b", coordMode: "schematic" },
  },
  woods: {
    dev_a: { pointMeta: "b", coordMode: "schematic" },
    dev_b: { pointMeta: "b", coordMode: "schematic" },
  },
  labyrinth: {
    dev_a: { pointMeta: "a", coordMode: "raster_tile", flipY: true },
    dev_b: { pointMeta: "a", coordMode: "raster_tile", flipY: true },
  },
  labs: {
    dev_a: { pointMeta: "a", coordMode: "schematic", flipY: true },
    dev_b: { pointMeta: "b", coordMode: "schematic", flipY: true },
  },
  shoreline: {
    dev_a: { pointMeta: "a", coordMode: "raster_crop", flipX: true },
    dev_b: { pointMeta: "b", coordMode: "schematic" },
  },
  groundzero: {
    dev_a: { pointMeta: "a", coordMode: "raster_crop", flipX: true },
    dev_b: { pointMeta: "b", coordMode: "schematic" },
  },
  reserve: {
    dev_a: { pointMeta: "b", coordMode: "schematic" },
    dev_b: { pointMeta: "b", coordMode: "schematic" },
  },
};

const MAP_PLAYER_PROFILES = {
  factory: {
    eftarkov: { swapGameAxes: true, flipX: true, flipY: true },
  },
  customs: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipY: true, headingOffset: 90 },
  },
  groundzero: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  interchange: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  lighthouse: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  shoreline: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  reserve: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  woods: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  streets: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  labyrinth: {
    dev_a: { headingOffset: -90 },
    dev_b: { headingOffset: -90 },
    eftarkov: { flipX: true, headingOffset: -90 },
  },
  labs: {
    dev_a: { flipHeadingY: true, flipHeadingX: true },
    dev_b: { flipHeadingY: true, flipHeadingX: true },
    eftarkov: { swapGameAxes: true, headingOffset: 180 },
  },
};

function playerMapProfile(mapId = state.currentId) {
  const key = devCoordProfileKey();
  const row = MAP_PLAYER_PROFILES[mapId]?.[key];
  return {
    flipY: Boolean(row?.flipY),
    flipX: Boolean(row?.flipX),
    swapGameAxes: Boolean(row?.swapGameAxes),
    flipHeadingY: Boolean(row?.flipHeadingY),
    flipHeadingX: Boolean(row?.flipHeadingX),
    headingOffset: Number(row?.headingOffset) || 0,
    positionRotate: Number(row?.positionRotate) || 0,
  };
}

function playerMarkerHeading(mapId, heading) {
  let h = Number(heading) || 0;
  const profile = playerMapProfile(mapId);
  if (profile.flipHeadingY) {
    h = (360 - h) % 360;
  }
  if (profile.flipHeadingX) {
    h = (180 - h + 360) % 360;
  }
  if (profile.headingOffset) {
    h = (h + profile.headingOffset + 360) % 360;
  }
  return h;
}

function gameToPlayerMapPixels(gameX, gameZ, meta, mapW, mapH, mapId = state.currentId) {
  const profile = playerMapProfile(mapId);
  let gx = gameX;
  let gz = gameZ;
  if (profile.swapGameAxes) {
    gx = gameZ;
    gz = gameX;
  }
  let pos = null;
  if (isEftarkovPointSource()) {
    pos = gameToComMapPixels(gx, gz, meta, mapW, mapH, mapId);
  } else {
    pos = gameToMapPixels(gx, gz, meta, mapW, mapH, mapId);
  }
  if (!pos) {
    return null;
  }
  if (profile.flipX) {
    pos.x = mapW - pos.x;
  }
  if (profile.flipY) {
    pos.y = mapH - pos.y;
  }
  if (profile.positionRotate) {
    pos = rotateMapPixels(pos.x, pos.y, mapW, mapH, profile.positionRotate);
  }
  return pos;
}

function devCoordProfileKey() {
  if (isEftarkovPointSource()) {
    return "eftarkov";
  }
  if (isDevPointSource()) {
    return `dev_${devMapVariant().toLowerCase()}`;
  }
  return "default";
}

function mapCoordProfile(mapId = state.currentId) {
  if (isEftarkovPointSource()) {
    if (mapId === "labyrinth") {
      return { pointMeta: "self", coordMode: "raster_tile", flipY: true };
    }
    return { pointMeta: "eftarkov", coordMode: "eftarkov", flipY: false };
  }
  const key = devCoordProfileKey();
  const byMap = MAP_COORD_PROFILES[mapId];
  if (byMap?.[key]) {
    return { ...DEFAULT_DEV_COORD_PROFILE, ...byMap[key] };
  }
  return {
    ...DEFAULT_DEV_COORD_PROFILE,
    pointMeta: key === "dev_b" ? "b" : "self",
  };
}

function shouldFlipMapY(mapId = state.currentId) {
  return Boolean(mapCoordProfile(mapId).flipY);
}

function shouldFlipMapX(mapId = state.currentId) {
  return Boolean(mapCoordProfile(mapId).flipX);
}

function usesDevAScaledCoords(mapId = state.currentId) {
  return Boolean(mapCoordProfile(mapId).scaleCoordsFromDevA) && isDevPointSource() && devMapVariant() === "B";
}

function devAMetaForMap(mapId = state.currentId) {
  return state.tarkovDevMeta?.[mapId] || null;
}

function pointMetaForMap(mapId = state.currentId) {
  const profile = mapCoordProfile(mapId);
  if (profile.pointMeta === "b") {
    return state.tarkovDevMetaB?.[mapId] || null;
  }
  if (profile.pointMeta === "a") {
    return devAMetaForMap(mapId);
  }
  if (isDevPointSource() && devMapVariant() === "B") {
    return state.tarkovDevMetaB?.[mapId] || state.mapMeta?.[mapId] || null;
  }
  return state.mapMeta?.[mapId] || state.tarkovDevMeta?.[mapId] || null;
}

function sizeMetaForMap(mapId = state.currentId) {
  const profile = mapCoordProfile(mapId);
  if (profile.sizeMeta === "b") {
    return state.tarkovDevMetaB?.[mapId] || state.mapMeta?.[mapId] || null;
  }
  if (profile.sizeMeta === "a") {
    return devAMetaForMap(mapId);
  }
  return pointMetaForMap(mapId);
}

function devDisplayMeta(mapId = state.currentId) {
  if (!isDevPointSource()) {
    return state.mapMeta?.[mapId] || null;
  }
  if (devMapVariant() === "B") {
    return sizeMetaForMap(mapId) || state.tarkovDevMetaB?.[mapId] || state.mapMeta?.[mapId] || null;
  }
  return state.tarkovDevMeta?.[mapId] || state.mapMeta?.[mapId] || null;
}

function tileZoomForMap(meta, mapW) {
  const fromMeta = Number(meta?.tile_zoom);
  if (Number.isFinite(fromMeta) && fromMeta >= 0) {
    return fromMeta;
  }
  if (mapW > 0) {
    return Math.max(0, Math.round(Math.log2(mapW / 256)));
  }
  return 4;
}

function usesRasterTileCoordsForProfile(mapId, meta, profile) {
  if (profile.coordMode === "raster_tile" || profile.coordMode === "raster_crop") {
    return true;
  }
  if (profile.coordMode === "schematic") {
    return false;
  }
  if (RASTER_TILE_MAPS.has(mapId)) {
    return true;
  }
  const zoom = Number(meta?.tile_zoom);
  return Number.isFinite(zoom) && zoom >= 0;
}

function usesRasterTileCoords(mapId, meta, coordVariant = null) {
  const profile = mapCoordProfile(mapId);
  if (isEftarkovPointSource()) {
    return profile.coordMode === "raster_tile" || profile.coordMode === "raster_crop";
  }
  return usesRasterTileCoordsForProfile(mapId, meta, profile);
}

function usesRasterCropPixels(mapId, meta, coordVariant = null) {
  if (!usesRasterTileCoords(mapId, meta, coordVariant)) {
    return false;
  }
  const stitchW = Number(meta.stitch_width);
  const stitchH = Number(meta.stitch_height);
  if (!(stitchW > 0 && stitchH > 0)) {
    return false;
  }
  const variant = coordVariant ?? (isDevPointSource() ? devMapVariant() : null);
  if (!isDevPointSource() || variant !== "B") {
    return true;
  }
  return usesDevAScaledCoords(mapId);
}


function gameToLayerPoint(gameX, gameZ, transform, rotation, zoom, mapId = state.currentId) {
  const point = gameToCrs(gameX, gameZ, transform, rotation, mapId);
  const factor = 2 ** zoom;
  return {
    x: point.x * factor,
    y: point.y * factor,
  };
}

function gameCornerLayerBounds(meta, transform, rotation, zoom) {
  const { xmin, xmax, zmin, zmax } = mappingExtents(meta);
  const corners = [
    [xmin, zmax],
    [xmax, zmin],
    [xmin, zmin],
    [xmax, zmax],
  ];
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, z] of corners) {
    const p = gameToLayerPoint(x, z, transform, rotation, zoom);
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  if (!Number.isFinite(minX) || maxX === minX || maxY === minY) {
    return null;
  }
  return { minX, minY, maxX, maxY };
}

function rasterLayerBounds(meta, transform, rotation, zoom) {
  const tileMinX = Number(meta.tile_min_x);
  const tileMinY = Number(meta.tile_min_y);
  const tileMaxX = Number(meta.tile_max_x);
  const tileMaxY = Number(meta.tile_max_y);
  if (
    Number.isFinite(tileMinX) &&
    Number.isFinite(tileMinY) &&
    Number.isFinite(tileMaxX) &&
    Number.isFinite(tileMaxY)
  ) {
    const tile = Number(meta.tile_size) || 256;
    return {
      minX: tileMinX * tile,
      minY: tileMinY * tile,
      maxX: (tileMaxX + 1) * tile,
      maxY: (tileMaxY + 1) * tile,
    };
  }
  return gameCornerLayerBounds(meta, transform, rotation, zoom);
}

function rasterPixelFromLayer(layer, bounds, meta, mapW, mapH, mapId = state.currentId, coordVariant = null) {
  const spanX = bounds.maxX - bounds.minX;
  const spanY = bounds.maxY - bounds.minY;
  if (!spanX || !spanY) {
    return null;
  }
  const nx = (layer.x - bounds.minX) / spanX;
  const ny = (layer.y - bounds.minY) / spanY;
  const stitchW = Number(meta.stitch_width);
  const stitchH = Number(meta.stitch_height);
  const offX = Number(meta.map_offset_x) || 0;
  const offY = Number(meta.map_offset_y) || 0;
  if (usesRasterCropPixels(mapId, meta, coordVariant)) {
    return { x: nx * stitchW - offX, y: ny * stitchH - offY };
  }
  return { x: nx * mapW, y: ny * mapH };
}

function layerNormFromMapPixels(pos, bounds, meta, mapW, mapH, mapId = state.currentId) {
  const spanX = bounds.maxX - bounds.minX;
  const spanY = bounds.maxY - bounds.minY;
  if (!spanX || !spanY) {
    return null;
  }
  const stitchW = Number(meta.stitch_width);
  const stitchH = Number(meta.stitch_height);
  const offX = Number(meta.map_offset_x) || 0;
  const offY = Number(meta.map_offset_y) || 0;
  if (usesRasterCropPixels(mapId, meta)) {
    return {
      nx: (pos.x + offX) / stitchW,
      ny: (pos.y + offY) / stitchH,
    };
  }
  return { nx: pos.x / mapW, ny: pos.y / mapH };
}

function gameToMapPixels(gameX, gameZ, meta, mapW, mapH, mapId = state.currentId) {
  if (!meta || !mapW || !mapH) {
    return null;
  }
  const transform = meta.transform;
  const rot = Number(meta.coordinates_rotation) || 180;
  let pos = null;
  if (Array.isArray(transform) && transform.length >= 4) {
    if (usesRasterTileCoords(mapId, meta)) {
      const zoom = tileZoomForMap(meta, mapW);
      const layer = gameToLayerPoint(gameX, gameZ, transform, rot, zoom, mapId);
      const bounds = rasterLayerBounds(meta, transform, rot, zoom);
      if (!bounds) {
        return null;
      }
      pos = rasterPixelFromLayer(layer, bounds, meta, mapW, mapH, mapId);
    } else {
      const ext = mappingExtents(meta);
      const sw = gameToCrs(ext.xmin, ext.zmin, transform, rot, mapId);
      const ne = gameToCrs(ext.xmax, ext.zmax, transform, rot, mapId);
      const point = gameToCrs(gameX, gameZ, transform, rot, mapId);
      const spanX = ne.x - sw.x;
      const spanY = sw.y - ne.y;
      if (!spanX || !spanY) {
        return null;
      }
      pos = {
        x: ((point.x - sw.x) / spanX) * mapW,
        y: ((point.y - ne.y) / spanY) * mapH,
      };
    }
  } else {
    const norm = normalizedGameCoords(gameX, gameZ, meta);
    if (!norm) {
      return null;
    }
    pos = {
      x: norm.u * mapW,
      y: norm.v * mapH,
    };
  }
  if (pos && usesDevAScaledCoords(mapId)) {
    const aMeta = devAMetaForMap(mapId);
    const aw = Number(aMeta?.width) || 0;
    const ah = Number(aMeta?.height) || 0;
    if (aw > 0 && ah > 0 && mapW > 0 && mapH > 0) {
      pos = { x: (pos.x / aw) * mapW, y: (pos.y / ah) * mapH };
    }
  }
  if (pos && shouldFlipMapX(mapId)) {
    pos.x = mapW - pos.x;
  }
  if (pos && shouldFlipMapY(mapId)) {
    pos.y = mapH - pos.y;
  }
  return rotateMapPixels(pos.x, pos.y, mapW, mapH, exfilMarkerRotationDegrees(mapId));
}

function unrotateMapPixels(x, y, mapW, mapH, degrees) {
  if (!degrees) {
    return { x, y };
  }
  const cx = mapW / 2;
  const cy = mapH / 2;
  const rad = (-degrees * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const dx = x - cx;
  const dy = y - cy;
  return {
    x: cx + dx * cos - dy * sin,
    y: cy + dx * sin + dy * cos,
  };
}

function crsToGame(crsX, crsY, transform, rotation, mapId = state.currentId) {
  const scaleX = Number(transform[0]);
  const marginX = Number(transform[1]);
  const scaleYRaw = Number(transform[2]);
  const marginY = Number(transform[3]);
  if (!scaleX || !scaleYRaw) {
    return null;
  }
  const lng = (crsX - marginX) / scaleX;
  const lat =
    mapId === "factory"
      ? (marginY - crsY) / scaleYRaw
      : (crsY - marginY) / scaleYRaw;
  const rot = ((Number(rotation) || 180) * Math.PI) / 180;
  const cos = Math.cos(rot);
  const sin = Math.sin(rot);
  return {
    x: -lat * sin + lng * cos,
    z: lat * cos + lng * sin,
  };
}

function mapPixelsToGame(px, py, meta, mapW, mapH, mapId = state.currentId) {
  if (!meta || !mapW || !mapH) {
    return null;
  }
  let pos = unrotateMapPixels(px, py, mapW, mapH, exfilMarkerRotationDegrees(mapId));
  if (shouldFlipMapX(mapId)) {
    pos.x = mapW - pos.x;
  }
  if (shouldFlipMapY(mapId)) {
    pos.y = mapH - pos.y;
  }
  let workMeta = meta;
  let workW = mapW;
  let workH = mapH;
  if (usesDevAScaledCoords(mapId)) {
    const aMeta = devAMetaForMap(mapId);
    const aw = Number(aMeta?.width) || 0;
    const ah = Number(aMeta?.height) || 0;
    if (!aMeta || !aw || !ah) {
      return null;
    }
    pos = { x: (pos.x / mapW) * aw, y: (pos.y / mapH) * ah };
    workMeta = aMeta;
    workW = aw;
    workH = ah;
  }
  const transform = workMeta.transform;
  const rot = Number(workMeta.coordinates_rotation) || 180;
  if (Array.isArray(transform) && transform.length >= 4) {
    if (usesRasterTileCoords(mapId, workMeta)) {
      const zoom = tileZoomForMap(workMeta, workW);
      const bounds = rasterLayerBounds(workMeta, transform, rot, zoom);
      if (!bounds) {
        return null;
      }
      const norm = layerNormFromMapPixels(pos, bounds, workMeta, workW, workH, mapId);
      if (!norm) {
        return null;
      }
      const layerX = bounds.minX + norm.nx * (bounds.maxX - bounds.minX);
      const layerY = bounds.minY + norm.ny * (bounds.maxY - bounds.minY);
      const factor = 2 ** zoom;
      return crsToGame(layerX / factor, layerY / factor, transform, rot, mapId);
    }
    const ext = mappingExtents(workMeta);
    const sw = gameToCrs(ext.xmin, ext.zmin, transform, rot, mapId);
    const ne = gameToCrs(ext.xmax, ext.zmax, transform, rot, mapId);
    const spanX = ne.x - sw.x;
    const spanY = sw.y - ne.y;
    if (!spanX || !spanY) {
      return null;
    }
    const crsX = sw.x + (pos.x / workW) * spanX;
    const crsY = ne.y + (pos.y / workH) * spanY;
    return crsToGame(crsX, crsY, transform, rot, mapId);
  }
  const u = pos.x / workW;
  const v = pos.y / workH;
  const { xmin, xmax, zmin, zmax } = mappingExtents(workMeta);
  const spanX = xmax - xmin;
  const spanZ = zmax - zmin;
  if (!spanX || !spanZ) {
    return null;
  }
  switch (rot) {
    case 90:
      return { x: xmin + v * spanX, z: zmax - u * spanZ };
    case 270:
      return { x: xmax - v * spanX, z: zmin + u * spanZ };
    case 0:
      return { x: xmin + u * spanX, z: zmin + v * spanZ };
    case 180:
    default:
      return { x: xmin + u * spanX, z: zmax - v * spanZ };
  }
}

function viewportClientToMapPixels(clientX, clientY) {
  const { iw, ih } = mapDimensions();
  if (!viewport || !iw || !ih || state.scale <= 0) {
    return null;
  }
  const rect = viewport.getBoundingClientRect();
  const cx = rect.left + rect.width / 2 + state.tx;
  const cy = rect.top + rect.height / 2 + state.ty;
  let dx = clientX - cx;
  let dy = clientY - cy;
  const rot = mapDisplayRotation();
  if (rot) {
    const rad = (-rot * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const rdx = dx * cos - dy * sin;
    const rdy = dx * sin + dy * cos;
    dx = rdx;
    dy = rdy;
  }
  const localX = dx / state.scale + iw / 2;
  const localY = dy / state.scale + ih / 2;
  if (localX < 0 || localY < 0 || localX > iw || localY > ih) {
    return null;
  }
  return { x: localX, y: localY };
}

function clientToGameCoords(clientX, clientY) {
  const mapId = state.currentId;
  const { iw, ih } = mapDimensions();
  const pos = viewportClientToMapPixels(clientX, clientY);
  if (!pos || !iw || !ih) {
    return null;
  }
  if (isEftarkovPointSource()) {
    const profile = mapCoordProfile(mapId);
    if (profile.coordMode === "raster_tile" || profile.coordMode === "raster_crop") {
      const pm = pointMetaForMap(mapId) || state.mapMeta?.[mapId];
      if (pm) {
        return mapPixelsToGame(pos.x, pos.y, pm, iw, ih, mapId);
      }
    }
    const layout = eftarkovLayoutForMap(mapId);
    if (!layout) {
      return null;
    }
    return eftarkovMapPixelsToGame(pos.x, pos.y, layout, iw, ih);
  }
  const pm = pointMetaForMap(mapId);
  if (pm) {
    return mapPixelsToGame(pos.x, pos.y, pm, iw, ih, mapId);
  }
  const meta = state.mapMeta?.[mapId];
  if (!meta) {
    return null;
  }
  return mapPixelsToGame(pos.x, pos.y, meta, iw, ih, mapId);
}

function formatGameCoordLabel(gameX, gameZ) {
  return `${formatCoord(gameX)}, ${formatCoord(gameZ)}`;
}

function gameCoordsForExfilEntry(entry, pos, mapId, iw, ih, meta) {
  if (isEftarkovPointSource()) {
    const game = mapPixelsToGame(pos.x, pos.y, meta, iw, ih, mapId);
    if (game) {
      return { x: game.x, z: game.z };
    }
    return null;
  }
  const coords = entry?.coordinates;
  if (!Array.isArray(coords) || coords.length < 2) {
    return null;
  }
  return { x: Number(coords[0]), z: Number(coords[1]) };
}

function appendMarkerCoordsLabel(parent, gameX, gameZ, color = null) {
  const labelEl = document.createElement("span");
  labelEl.className = "marker-coords-label";
  labelEl.textContent = formatGameCoordLabel(gameX, gameZ);
  if (color) {
    labelEl.style.color = color;
  }
  parent.appendChild(labelEl);
}

function formatCoord(value) {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return String(Math.round(value * 10) / 10);
}

function clearMouseCoordsDisplay() {
  if (mouseCoordX) {
    mouseCoordX.textContent = "—";
  }
  if (mouseCoordY) {
    mouseCoordY.textContent = "—";
  }
}

let mouseCoordRaf = 0;

function updateMouseCoordsDisplay(clientX, clientY) {
  if (!mouseCoordX || !mouseCoordY) {
    return;
  }
  const coords = clientToGameCoords(clientX, clientY);
  if (!coords) {
    clearMouseCoordsDisplay();
    return;
  }
  mouseCoordX.textContent = formatCoord(coords.x);
  mouseCoordY.textContent = formatCoord(coords.z);
}

function scheduleMouseCoordsUpdate(clientX, clientY) {
  if (mouseCoordRaf) {
    cancelAnimationFrame(mouseCoordRaf);
  }
  mouseCoordRaf = requestAnimationFrame(() => {
    mouseCoordRaf = 0;
    updateMouseCoordsDisplay(clientX, clientY);
  });
}

function mapMetaCacheKey() {
  if (isDevPointSource()) {
    return `tarkovdev:${devMapVariant()}`;
  }
  return state.pointSource;
}

function mapSourceQuery() {
  if (isDevPointSource()) {
    return `source=tarkovdev&variant=${encodeURIComponent(devMapVariant().toLowerCase())}`;
  }
  if (isEftarkovPointSource()) {
    return "source=eftarkov";
  }
  return `source=${encodeURIComponent(state.pointSource)}`;
}

function mapCacheKey(mapId) {
  if (isDevPointSource()) {
    return `tarkovdev:${devMapVariant()}:${mapId}`;
  }
  return `${state.pointSource}:${mapId}`;
}

function mapAssetRevision(mapId = state.currentId) {
  const rev = state.mapMeta?.[mapId]?.map_asset_rev;
  return rev ? String(rev) : "";
}

function mapFetchUrl(entry) {
  const base = entry.svgUrl || `/api/map/${encodeURIComponent(entry.id)}?${mapSourceQuery()}`;
  const rev = mapAssetRevision(entry.id);
  if (!rev) {
    return base;
  }
  const sep = base.includes("?") ? "&" : "?";
  return `${base}${sep}rev=${encodeURIComponent(rev)}`;
}

function mapOverlayFetchUrl(mapId) {
  const base = mapOverlayUrl(mapId);
  if (!base) {
    return null;
  }
  const rev = mapAssetRevision(mapId);
  if (!rev) {
    return base;
  }
  const sep = base.includes("?") ? "&" : "?";
  return `${base}${sep}rev=${encodeURIComponent(rev)}`;
}

function invalidateMapContentCacheIfStale(mapId) {
  const key = mapCacheKey(mapId);
  const cached = mapContentCache.get(key);
  const rev = mapAssetRevision(mapId);
  if (!cached) {
    return;
  }
  if (rev && cached.rev !== rev) {
    if (cached.kind === "raster" || cached.kind === "rasterOverlay") {
      revokeRasterCacheUrl(cached);
    }
    mapContentCache.delete(key);
  }
}

function devPointMetaForMap(mapId = state.currentId) {
  return pointMetaForMap(mapId);
}

function eftarkovLayoutForMap(mapId) {
  const meta = state.mapMeta?.[mapId];
  if (meta && meta.eftarkov_cols) {
    return {
      cols: Number(meta.eftarkov_cols),
      rows: Number(meta.eftarkov_rows),
      tile_size: Number(meta.eftarkov_tile_size) || 256,
      offset_x: Number(meta.map_offset_x) || 0,
      offset_y: Number(meta.map_offset_y) || 0,
    };
  }
  const fallback = state.eftarkovMeta?.[mapId];
  if (!fallback) {
    return null;
  }
  return {
    cols: Number(fallback.cols),
    rows: Number(fallback.rows),
    tile_size: Number(fallback.tile_size) || 256,
    offset_x: 0,
    offset_y: 0,
  };
}

function eftarkovMapPixelsToGame(px, py, layout, mapW, mapH) {
  if (!layout || !mapW || !mapH) {
    return null;
  }
  const cols = Number(layout.cols);
  const rows = Number(layout.rows);
  const tile = Number(layout.tile_size) || 256;
  if (!cols || !rows) {
    return null;
  }
  const offX = Number(layout.offset_x) || 0;
  const offY = Number(layout.offset_y) || 0;
  const ew = cols * tile;
  const eh = rows * tile;
  const cw = ew - offX;
  const ch = eh - offY;
  const sx = mapW < cw ? (px / mapW) * cw : px;
  const sy = mapH < ch ? py : (py / mapH) * ch;
  const mapX = sx - ew / 2 + offX;
  const mapY = sy - eh / 2 + offY;
  return { x: mapX, z: mapY };
}

function gameToEftarkovMapPixels(gameX, gameZ, layout, mapW, mapH) {
  if (!layout || !mapW || !mapH) {
    return null;
  }
  const cols = Number(layout.cols);
  const rows = Number(layout.rows);
  const tile = Number(layout.tile_size) || 256;
  if (!cols || !rows) {
    return null;
  }
  const offX = Number(layout.offset_x) || 0;
  const offY = Number(layout.offset_y) || 0;
  const ew = cols * tile;
  const eh = rows * tile;
  const cw = ew - offX;
  const ch = eh - offY;
  const sx = gameX + ew / 2 - offX;
  const sy = gameZ + eh / 2 - offY;
  const px = mapW < cw ? (sx / cw) * mapW : sx;
  const py = mapH < ch ? sy : (sy / ch) * mapH;
  return { x: px, y: py };
}

function gameToComMapPixels(gameX, gameZ, meta, mapW, mapH, mapId = state.currentId) {
  const profile = mapCoordProfile(mapId);
  if (profile.coordMode === "raster_tile" || profile.coordMode === "raster_crop") {
    const pm = pointMetaForMap(mapId) || meta;
    return pm ? gameToMapPixels(gameX, gameZ, pm, mapW, mapH, mapId) : null;
  }
  const layout = eftarkovLayoutForMap(mapId);
  if (!layout) {
    return null;
  }
  return gameToEftarkovMapPixels(gameX, gameZ, layout, mapW, mapH);
}

function comPlayerOverlayReady(mapId = state.currentId) {
  const profile = mapCoordProfile(mapId);
  if (profile.coordMode === "raster_tile" || profile.coordMode === "raster_crop") {
    return Boolean(pointMetaForMap(mapId) || state.mapMeta?.[mapId]);
  }
  return Boolean(eftarkovLayoutForMap(mapId));
}

function comPointToMapPixels(entry, mapW, mapH) {
  const display = entry?.display_coordinates;
  if (Array.isArray(display) && display.length >= 2) {
    return { x: Number(display[0]), y: Number(display[1]) };
  }
  return null;
}

function pointToMapPixels(coords, meta, mapW, mapH, mapId = state.currentId) {
  if (!Array.isArray(coords) || coords.length < 2) {
    return null;
  }
  const pm = pointMetaForMap(mapId);
  return gameToMapPixels(Number(coords[0]), Number(coords[1]), pm || meta, mapW, mapH, mapId);
}

function exfilCountForMap(kind, mapId = state.currentId) {
  const data = syncActiveExfilData();
  return (data?.[kind]?.[mapId] || []).length;
}

function visibleExfilKinds() {
  return EXFIL_KINDS.map(({ kind }) => kind);
}

function syncExfilGroupCheckbox() {
  if (!exfilGroupToggle) {
    return;
  }
  const kinds = visibleExfilKinds();
  const enabled = kinds.filter((kind) => state.exfilFilters[kind]);
  exfilGroupToggle.checked = enabled.length === kinds.length && kinds.length > 0;
  exfilGroupToggle.indeterminate = enabled.length > 0 && enabled.length < kinds.length;
}

function refreshExfilFilterVisibility() {
  syncExfilGroupCheckbox();
}

function refreshExfilFilterLabels() {
  if (pointsSelectLabel) {
    pointsSelectLabel.textContent = t("marker_points_panel", "點位");
  }
  if (exfilFilterLabels.group) {
    exfilFilterLabels.group.textContent = t("marker_exfil_group", "撤離點");
  }
  for (const { kind, labelKey, fallback, color } of EXFIL_KINDS) {
    const el = exfilFilterLabels[kind];
    if (el) {
      el.textContent = t(labelKey, fallback);
      el.style.color = color;
    }
  }
  if (exfilFilterLabels.pmcNames) {
    exfilFilterLabels.pmcNames.textContent = t("marker_exfil_show_names", "撤離點名稱");
  }
  if (exfilFilterLabels.showCoords) {
    exfilFilterLabels.showCoords.textContent = t("marker_show_coords", "顯示座標");
  }
  if (exfilFilterLabels.player) {
    exfilFilterLabels.player.textContent = t("marker_player_position", "玩家位置");
  }
  if (exfilFilterLabels.playerLock) {
    exfilFilterLabels.playerLock.textContent = t("marker_player_center_lock", "玩家中心鎖定");
  }
}

function refreshEmbeddedLabels() {
  if (embeddedFilterLabels.panel) {
    embeddedFilterLabels.panel.textContent = t("embedded_panel_label", "內嵌地圖");
  }
  if (embeddedFilterLabels.displayTarget) {
    embeddedFilterLabels.displayTarget.textContent = t("embedded_display_target", "顯示於");
  }
  if (embeddedFilterLabels.position) {
    embeddedFilterLabels.position.textContent = t("embedded_position", "位置");
  }
  if (embeddedFilterLabels.range) {
    embeddedFilterLabels.range.textContent = t("embedded_range", "顯示範圍");
  }
  if (embeddedFilterLabels.size) {
    embeddedFilterLabels.size.textContent = t("embedded_size", "顯示尺寸");
  }
  if (embeddedFilterLabels.offsetX) {
    embeddedFilterLabels.offsetX.textContent = t("embedded_offset_x", "偏移 X");
  }
  if (embeddedFilterLabels.offsetY) {
    embeddedFilterLabels.offsetY.textContent = t("embedded_offset_y", "偏移 Y");
  }
  if (embeddedFilterLabels.opacity) {
    embeddedFilterLabels.opacity.textContent = t("embedded_opacity", "透明度");
  }
  if (embeddedPositionSelect) {
    for (const opt of embeddedPositionSelect.options) {
      opt.textContent = t(`embedded_position_${opt.value.replace(/-/g, "_")}`, opt.textContent);
    }
  }
  if (embeddedRangeSelect) {
    for (const opt of embeddedRangeSelect.options) {
      opt.textContent = t(`embedded_range_${opt.value}x`, opt.textContent);
    }
  }
  if (embeddedSizeSelect) {
    for (const opt of embeddedSizeSelect.options) {
      opt.textContent = t(`embedded_size_${opt.value}`, opt.textContent);
    }
  }
  for (const select of [embeddedOffsetXSelect, embeddedOffsetYSelect]) {
    if (!select) {
      continue;
    }
    for (const opt of select.options) {
      opt.textContent = t(`embedded_offset_${opt.value}`, opt.textContent);
    }
  }
  if (embeddedOpacitySelect) {
    for (const opt of embeddedOpacitySelect.options) {
      opt.textContent = t(`embedded_opacity_${opt.value}`, opt.textContent);
    }
  }
  refreshEmbeddedDisplayStatus();
}

function embeddedDisplayTargetText(target) {
  switch (target) {
    case "game":
      return t("embedded_display_game", "遊戲");
    case "screen":
      return t("embedded_display_screen", "主螢幕");
    default:
      return t("embedded_display_none", "—");
  }
}

function applyEmbeddedDisplayStatus(data) {
  const target = data?.display?.target || "none";
  state.embeddedDisplayTarget = target;
  if (embeddedDisplayTargetValue) {
    embeddedDisplayTargetValue.textContent = embeddedDisplayTargetText(target);
    embeddedDisplayTargetValue.dataset.target = target;
  }
}

async function refreshEmbeddedDisplayStatus() {
  try {
    const res = await fetch("/api/embedded/state", { cache: "no-store" });
    if (!res.ok) {
      return;
    }
    applyEmbeddedDisplayStatus(await res.json());
  } catch {
  }
}

let embeddedStatusTimer = null;

function startEmbeddedStatusPoll() {
  refreshEmbeddedDisplayStatus();
  if (embeddedStatusTimer) {
    window.clearInterval(embeddedStatusTimer);
  }
  embeddedStatusTimer = window.setInterval(refreshEmbeddedDisplayStatus, 500);
}

function stopEmbeddedStatusPoll() {
  if (embeddedStatusTimer) {
    window.clearInterval(embeddedStatusTimer);
    embeddedStatusTimer = null;
  }
}

function syncEmbeddedStatusPolling() {
  if (state.embeddedPosition !== "none") {
    startEmbeddedStatusPoll();
    return;
  }
  if (embeddedPanel && !embeddedPanel.classList.contains("hidden")) {
    startEmbeddedStatusPoll();
    return;
  }
  stopEmbeddedStatusPoll();
  refreshEmbeddedDisplayStatus();
}

function readEmbeddedControls() {
  state.embeddedPosition = embeddedPositionSelect?.value || "none";
  state.embeddedRange = Number(embeddedRangeSelect?.value) || 10;
  state.embeddedSize = Number(embeddedSizeSelect?.value) || 300;
  state.embeddedOffsetX = Number(embeddedOffsetXSelect?.value) || 250;
  state.embeddedOffsetY = Number(embeddedOffsetYSelect?.value) || 0;
  state.embeddedOpacity = Number(embeddedOpacitySelect?.value) || 50;
}

function syncEmbeddedControlsFromState() {
  if (embeddedPositionSelect) {
    embeddedPositionSelect.value = state.embeddedPosition;
  }
  if (embeddedRangeSelect) {
    embeddedRangeSelect.value = String(state.embeddedRange);
  }
  if (embeddedSizeSelect) {
    embeddedSizeSelect.value = String(state.embeddedSize);
  }
  if (embeddedOffsetXSelect) {
    embeddedOffsetXSelect.value = String(state.embeddedOffsetX);
  }
  if (embeddedOffsetYSelect) {
    embeddedOffsetYSelect.value = String(state.embeddedOffsetY);
  }
  if (embeddedOpacitySelect) {
    embeddedOpacitySelect.value = String(state.embeddedOpacity);
  }
}

function syncEmbeddedPlayerLockUI() {
  const active = state.embeddedPosition !== "none";
  if (active) {
    state.playerCenterLock = true;
    if (exfilPlayerLockToggle) {
      exfilPlayerLockToggle.checked = true;
      exfilPlayerLockToggle.disabled = true;
    }
    applyPlayerCenterLock();
  } else if (exfilPlayerLockToggle) {
    exfilPlayerLockToggle.disabled = false;
  }
}

function embeddedPlayerMapPixelPosition(mapId = state.currentId) {
  const loc = state.playerLocation;
  if (!loc?.valid) {
    return null;
  }
  const meta = isDevPointSource()
    ? pointMetaForMap(mapId) || state.mapMeta?.[mapId]
    : state.mapMeta?.[mapId];
  const { iw, ih } = mapDimensions();
  const ready = isEftarkovPointSource()
    ? Boolean(comPlayerOverlayReady(mapId) && iw && ih)
    : Boolean(meta && iw && ih);
  if (!ready) {
    return null;
  }
  return gameToPlayerMapPixels(
    Number(loc.x),
    Number(loc.z),
    meta || state.mapMeta?.[mapId],
    iw,
    ih,
    mapId
  );
}

function computeEmbeddedExfilMarkers(mapId, iw, ih) {
  const markers = [];
  const meta = state.mapMeta?.[mapId] || pointMetaForMap(mapId);
  const eftReady =
    isEftarkovPointSource() &&
    Boolean(eftarkovLayoutForMap(mapId) || state.mapMeta?.[mapId]?.width);
  if ((!meta && !eftReady) || !iw || !ih) {
    return markers;
  }
  const exfilData = syncActiveExfilData();
  if (!exfilData) {
    return markers;
  }
  const coordMeta = pointMetaForMap(mapId) || meta || {};
  for (const { kind, icon, color } of EXFIL_KINDS) {
    if (!state.exfilFilters[kind]) {
      continue;
    }
    if (kind === "coop" && exfilCountForMap("coop", mapId) === 0) {
      continue;
    }
    const points = (exfilData[kind] || {})[mapId] || [];
    for (const entry of points) {
      const coords = entry?.coordinates;
      if (!Array.isArray(coords) || coords.length < 2) {
        continue;
      }
      let pos = isEftarkovPointSource() ? comPointToMapPixels(entry, iw, ih) : null;
      if (!pos) {
        pos = pointToMapPixels(coords, coordMeta, iw, ih, mapId);
      }
      if (!pos) {
        continue;
      }
      const rawName = entry.name ? String(entry.name).trim() : "";
      const exfilId = entry.id ? String(entry.id).trim() : "";
      const name = exfilLabel(exfilId, rawName);
      const gameCoords = gameCoordsForExfilEntry(entry, pos, mapId, iw, ih, meta);
      const marker = {
        kind,
        x: pos.x,
        y: pos.y,
        icon,
        color,
        zIndex: EXFIL_LAYER_Z[kind] || 0,
      };
      if (name) {
        marker.name = name.toUpperCase();
      }
      if (gameCoords) {
        marker.gameX = gameCoords.x;
        marker.gameZ = gameCoords.z;
      }
      markers.push(marker);
    }
  }
  return markers;
}

function computeEmbeddedViewport() {
  if (state.embeddedPosition === "none") {
    return null;
  }
  const size = state.embeddedSize;
  const range = state.embeddedRange;
  const mapId = state.currentId;
  const pos = embeddedPlayerMapPixelPosition();
  const { iw, ih } = mapDimensions();
  if (!pos || !iw || !ih || !size || !range) {
    return null;
  }
  const fitScale = size / Math.max(iw, ih);
  const scale = fitScale * range;
  const rot = mapDisplayRotation();
  const ox = pos.x - iw / 2;
  const oy = pos.y - ih / 2;
  const rad = (rot * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const rx = ox * cos - oy * sin;
  const ry = ox * sin + oy * cos;
  const entry = currentMapEntry();
  const mapUrl = entry ? mapFetchUrl(entry) : "";
  const loc = state.playerLocation;
  const rawHeading = loc?.valid ? Number(loc.rotation) : 0;
  const heading = loc?.valid ? playerMarkerHeading(state.currentId, rawHeading) : 0;
  const imgRot = rot ? heading - rot : heading;
  let player = null;
  if (state.showPlayer && pos) {
    player = {
      x: pos.x,
      y: pos.y,
      heading,
      imgRot,
    };
    if (loc?.valid) {
      player.gameX = Number(loc.x);
      player.gameZ = Number(loc.z);
    }
  }
  return {
    scale,
    tx: -rx * scale,
    ty: -ry * scale,
    rotation: rot,
    iw,
    ih,
    mapUrl,
    showNames: state.exfilShowNames,
    showCoords: state.showMarkerCoords,
    showPlayer: state.showPlayer,
    markers: computeEmbeddedExfilMarkers(mapId, iw, ih),
    player,
  };
}

async function pushEmbeddedContext() {
  if (state.embeddedPosition === "none") {
    return;
  }
  try {
    await fetch("/api/embedded/context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mapId: state.currentId,
        pointSource: state.pointSource,
      }),
    });
  } catch {
  }
}

async function pushEmbeddedSettings() {
  readEmbeddedControls();
  syncEmbeddedPlayerLockUI();
  try {
    await fetch("/api/embedded/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        position: state.embeddedPosition,
        range: state.embeddedRange,
        size: state.embeddedSize,
        offsetX: state.embeddedOffsetX,
        offsetY: state.embeddedOffsetY,
        opacity: state.embeddedOpacity,
      }),
    });
  } catch {
  }
  await pushEmbeddedContext();
  pushEmbeddedViewport();
  syncEmbeddedStatusPolling();
}

function pushEmbeddedViewport() {
  if (state.embeddedPosition === "none") {
    return;
  }
  const viewport = computeEmbeddedViewport();
  if (!viewport) {
    return;
  }
  fetch("/api/embedded/viewport", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(viewport),
  }).catch(() => {});
}

async function loadEmbeddedSettings() {
  try {
    const res = await fetch("/api/embedded/settings", { cache: "no-store" });
    if (!res.ok) {
      return;
    }
    const data = await res.json();
    state.embeddedPosition = data.position || "none";
    state.embeddedRange = Number(data.range) || 10;
    state.embeddedSize = Number(data.size) || 300;
    state.embeddedOffsetX = Number(data.offsetX ?? data.offset) || 250;
    state.embeddedOffsetY = Number(data.offsetY) || 0;
    state.embeddedOpacity = Number(data.opacity) || 50;
    syncEmbeddedControlsFromState();
    syncEmbeddedPlayerLockUI();
    syncEmbeddedStatusPolling();
  } catch {
  }
}

async function loadMapMeta(force = false) {
  const cacheKey = mapMetaCacheKey();
  if (!force && state.mapMetaBySource[cacheKey]) {
    state.mapMeta = state.mapMetaBySource[cacheKey];
    return state.mapMeta;
  }
  const res = await fetch(`/api/maps/bounds?${mapSourceQuery()}`, { cache: "no-store" });
  if (!res.ok) {
    return null;
  }
  const data = await res.json();
  state.mapMetaBySource[cacheKey] = data;
  state.mapMeta = data;
  return state.mapMeta;
}

async function loadEftarkovMeta(force = false) {
  if (!force && state.eftarkovMeta) {
    return state.eftarkovMeta;
  }
  const res = await fetch("/api/points/eftarkov/meta", { cache: "no-store" });
  if (!res.ok) {
    return null;
  }
  state.eftarkovMeta = await res.json();
  return state.eftarkovMeta;
}

function isEftarkovExfilData(data) {
  const pmc = data?.pmc;
  if (!pmc || typeof pmc !== "object") {
    return false;
  }
  for (const mapId of Object.keys(pmc)) {
    const rows = pmc[mapId];
    if (!Array.isArray(rows) || rows.length === 0) {
      continue;
    }
    const coords = rows[0]?.coordinates;
    if (!Array.isArray(coords) || coords.length < 2) {
      continue;
    }
    const mag = Math.max(Math.abs(Number(coords[0])), Math.abs(Number(coords[1])));
    if (mag > 500) {
      return true;
    }
  }
  return false;
}

function syncActiveExfilData() {
  const key = pointsApiSource();
  const cached = state.exfilDataBySource[key];
  if (cached) {
    state.exfilData = cached;
    return cached;
  }
  return state.exfilData;
}

async function loadExfilData(force = false) {
  const cacheKey = pointsApiSource();
  if (!force && state.exfilDataBySource[cacheKey]) {
    state.exfilData = state.exfilDataBySource[cacheKey];
    return state.exfilData;
  }
  const out = {};
  await Promise.all(
    EXFIL_KINDS.map(async ({ kind }) => {
      const res = await fetch(`/api/points/exfil/${kind}?source=${encodeURIComponent(cacheKey)}`, {
        cache: "no-store",
      });
      if (!res.ok) {
        out[kind] = {};
        return;
      }
      try {
        out[kind] = await res.json();
      } catch {
        out[kind] = {};
      }
    })
  );

  state.exfilDataBySource[cacheKey] = out;
  state.exfilData = out;
  return out;
}

async function ensureComPointData() {
  if (!isEftarkovPointSource()) {
    return;
  }
  const cacheKey = mapMetaCacheKey();
  if (state.mapMetaBySource[cacheKey]) {
    state.mapMeta = state.mapMetaBySource[cacheKey];
  }
  const tasks = [];
  if (!state.mapMetaBySource[cacheKey]) {
    tasks.push(loadMapMeta(true));
  }
  if (!state.eftarkovMeta) {
    tasks.push(loadEftarkovMeta(true));
  }
  if (!state.tarkovDevMeta) {
    tasks.push(loadTarkovDevMeta());
  }
  const eftCached = state.exfilDataBySource.eftarkov;
  if (!eftCached || !isEftarkovExfilData(eftCached)) {
    tasks.push(loadExfilData(true));
  } else {
    state.exfilData = eftCached;
  }
  if (tasks.length) {
    await Promise.allSettled(tasks);
  }
}

async function cyclePointSource() {
  const idx = POINT_SOURCES.findIndex((s) => s.id === state.pointSource);
  const next = POINT_SOURCES[(idx + 1) % POINT_SOURCES.length];
  state.pointSource = next.id;
  localStorage.setItem(POINT_SOURCE_KEY, next.id);
  refreshPointSourceLabel();
  invalidateOverlays();
  clearMapContentCache();
  try {
    await reloadMapCatalog();
  } catch {
    setSelectErrorLabel();
    return;
  }
  try {
    await Promise.all([loadMapMeta(true), loadEftarkovMeta(true), loadExfilData(true)]);
    syncActiveExfilData();
  } catch {
  }
  const nextId = state.maps.some((m) => m.id === state.currentId)
    ? state.currentId
    : pickInitialMap();
  setMap(nextId);
}

function mappingExtents(meta) {
  const xmin = Number(meta.svg_xmin);
  const xmax = Number(meta.svg_xmax);
  const zmin = Number(meta.svg_zmin);
  const zmax = Number(meta.svg_zmax);
  if ([xmin, xmax, zmin, zmax].every((v) => Number.isFinite(v))) {
    return { xmin, xmax, zmin, zmax };
  }
  return {
    xmin: Number(meta.xmin),
    xmax: Number(meta.xmax),
    zmin: Number(meta.zmin),
    zmax: Number(meta.zmax),
  };
}

function applyRotationLatLng(lat, lng, rotation) {
  if (!rotation) {
    return { lat, lng };
  }
  const rad = (rotation * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return {
    lat: lng * sin + lat * cos,
    lng: lng * cos - lat * sin,
  };
}

function gameToCrs(gameX, gameZ, transform, rotation, mapId = state.currentId) {
  const scaleX = Number(transform[0]);
  const marginX = Number(transform[1]);
  const scaleY = Number(transform[2]) * -1;
  const marginY = Number(transform[3]);
  const { lat, lng } = applyRotationLatLng(gameZ, gameX, rotation);
  const crsY =
    mapId === "factory" ? scaleY * lat + marginY : scaleY * -lat + marginY;
  return {
    x: scaleX * lng + marginX,
    y: crsY,
  };
}

function normalizedGameCoords(gameX, gameZ, meta) {
  const { xmin, xmax, zmin, zmax } = mappingExtents(meta);
  const spanX = xmax - xmin;
  const spanZ = zmax - zmin;
  if (!spanX || !spanZ) {
    return null;
  }
  const rot = Number(meta.coordinates_rotation) || 180;
  switch (rot) {
    case 90:
      return {
        u: (zmax - gameZ) / spanZ,
        v: (gameX - xmin) / spanX,
      };
    case 270:
      return {
        u: (gameZ - zmin) / spanZ,
        v: (xmax - gameX) / spanX,
      };
    case 0:
      return {
        u: (gameX - xmin) / spanX,
        v: (gameZ - zmin) / spanZ,
      };
    case 180:
    default:
      return {
        u: (gameX - xmin) / spanX,
        v: (zmax - gameZ) / spanZ,
      };
  }
}

function invalidateOverlays() {
  state.overlayGeneration += 1;
  clearPointOverlays();
}

function clearPointOverlays() {
  if (exfilOverlay) {
    exfilOverlay.replaceChildren();
  }
  if (playerOverlay) {
    playerOverlay.replaceChildren();
  }
}

function refreshPointOverlays(loadToken = state.mapLoadToken) {
  if (loadToken !== state.mapLoadToken) {
    clearPointOverlays();
    return;
  }
  renderExfilOverlay();
  renderPlayerOverlay();
  applyPlayerCenterLock();
  pushEmbeddedViewport();
}

function playerMapPixelPosition(mapId = state.currentId) {
  if (!state.showPlayer) {
    return null;
  }
  const loc = state.playerLocation;
  if (!loc?.valid) {
    return null;
  }
  const meta = isDevPointSource()
    ? pointMetaForMap(mapId) || state.mapMeta?.[mapId]
    : state.mapMeta?.[mapId];
  const { iw, ih } = mapDimensions();
  const ready = isEftarkovPointSource()
    ? Boolean(comPlayerOverlayReady(mapId) && iw && ih)
    : Boolean(meta && iw && ih);
  if (!ready) {
    return null;
  }
  return gameToPlayerMapPixels(
    Number(loc.x),
    Number(loc.z),
    meta || state.mapMeta?.[mapId],
    iw,
    ih,
    mapId
  );
}

function applyPlayerCenterLock() {
  if (!state.playerCenterLock) {
    return;
  }
  const pos = playerMapPixelPosition();
  const { iw, ih } = mapDimensions();
  if (!pos || !iw || !ih || state.scale <= 0) {
    return;
  }
  const ox = pos.x - iw / 2;
  const oy = pos.y - ih / 2;
  const rot = mapDisplayRotation();
  const rad = (rot * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const rx = ox * cos - oy * sin;
  const ry = ox * sin + oy * cos;
  state.tx = -rx * state.scale;
  state.ty = -ry * state.scale;
  applyTransform();
}

async function loadTarkovDevMeta() {
  if (state.tarkovDevMeta) {
    return state.tarkovDevMeta;
  }
  const res = await fetch("/api/maps/bounds?source=tarkovdev");
  if (!res.ok) {
    return null;
  }
  state.tarkovDevMeta = await res.json();
  return state.tarkovDevMeta;
}

async function loadTarkovDevMetaB() {
  if (state.tarkovDevMetaB) {
    return state.tarkovDevMetaB;
  }
  const res = await fetch("/api/maps/bounds?source=tarkovdev&variant=b");
  if (!res.ok) {
    return null;
  }
  state.tarkovDevMetaB = await res.json();
  return state.tarkovDevMetaB;
}

function exfilIconURL(iconName) {
  return `/api/points/icons/${iconName}.png`;
}

function playerIconURL() {
  return "/api/points/icons/player.png";
}

const MARKER_ICON_SIZE = 24;

function markerPositionStyle(pos, mapW, mapH) {
  return {
    left: `${(pos.x / mapW) * 100}%`,
    top: `${(pos.y / mapH) * 100}%`,
    width: `${MARKER_ICON_SIZE}px`,
    height: `${MARKER_ICON_SIZE}px`,
  };
}

function markerCenterTransform(mapId = state.currentId, heading = null) {
  let transform = "translate(-50%, -50%)";
  const rot = displayRotationForMap(mapId);
  if (heading != null) {
    const imgRot = rot ? heading - rot : heading;
    transform += ` rotate(${-imgRot}deg)`;
  } else if (rot) {
    transform += ` rotate(${-rot}deg)`;
  }
  return transform;
}

function syncMarkerLabelVisibility() {
  if (exfilOverlay) {
    exfilOverlay.classList.toggle("hide-exfil-names", !state.exfilShowNames);
    exfilOverlay.classList.toggle("hide-marker-coords", !state.showMarkerCoords);
  }
  if (playerOverlay) {
    playerOverlay.classList.toggle("hide-marker-coords", !state.showMarkerCoords);
  }
  if (state.embeddedPosition !== "none") {
    pushEmbeddedViewport();
  }
}

function syncExfilNameVisibility() {
  syncMarkerLabelVisibility();
}

function renderExfilOverlay() {
  if (!exfilOverlay) {
    return;
  }
  const gen = state.overlayGeneration;
  exfilOverlay.replaceChildren();

  const mapId = state.currentId;
  const source = state.pointSource;
  const variant = devMapVariant();
  const meta = state.mapMeta?.[mapId] || pointMetaForMap(mapId);
  const eftReady =
    isEftarkovPointSource() &&
    Boolean(eftarkovLayoutForMap(mapId) || state.mapMeta?.[mapId]?.width);
  const { iw, ih } = mapDimensions();
  if (
    gen !== state.overlayGeneration ||
    mapId !== state.currentId ||
    source !== state.pointSource ||
    (isDevPointSource(source) && variant !== devMapVariant()) ||
    (!meta && !eftReady) ||
    !iw ||
    !ih
  ) {
    return;
  }

  const exfilData = syncActiveExfilData();
  if (!exfilData) {
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const { kind, icon, color } of EXFIL_KINDS) {
    if (gen !== state.overlayGeneration) {
      return;
    }
    if (!state.exfilFilters[kind]) {
      continue;
    }
    if (kind === "coop" && exfilCountForMap("coop", mapId) === 0) {
      continue;
    }
    const byMap = exfilData[kind] || {};
    const points = byMap[mapId] || [];
    for (const entry of points) {
      const coords = entry?.coordinates;
      if (!Array.isArray(coords) || coords.length < 2) {
        continue;
      }
      const coordMeta = pointMetaForMap(mapId) || meta || {};
      let pos = isEftarkovPointSource() ? comPointToMapPixels(entry, iw, ih) : null;
      if (!pos) {
        pos = pointToMapPixels(coords, coordMeta, iw, ih, mapId);
      }
      if (!pos) {
        continue;
      }
      const marker = document.createElement("div");
      marker.className = "exfil-marker";
      marker.dataset.exfil = kind;
      marker.style.zIndex = String(EXFIL_LAYER_Z[kind] || 0);
      Object.assign(marker.style, markerPositionStyle(pos, iw, ih));
      marker.style.transform = markerCenterTransform(mapId);
      const rawName = entry.name ? String(entry.name).trim() : "";
      const exfilId = entry.id ? String(entry.id).trim() : "";
      const name = exfilLabel(exfilId, rawName);
      const img = document.createElement("img");
      img.src = exfilIconURL(icon);
      img.alt = name ? `${kind}: ${name}` : kind;
      img.draggable = false;
      marker.appendChild(img);
      if (name) {
        const labelEl = document.createElement("span");
        labelEl.className = "exfil-marker-label";
        labelEl.textContent = name.toUpperCase();
        labelEl.style.color = color;
        marker.appendChild(labelEl);
      }
      const gameCoords = gameCoordsForExfilEntry(entry, pos, mapId, iw, ih, meta);
      if (gameCoords) {
        appendMarkerCoordsLabel(marker, gameCoords.x, gameCoords.z, color);
      }
      fragment.appendChild(marker);
    }
  }
  if (gen !== state.overlayGeneration) {
    return;
  }
  exfilOverlay.replaceChildren(fragment);
  syncMarkerLabelVisibility();
}

const PLAYER_MARKER_SIZE = 28;

function playerMarkerRotation(mapId, heading) {
  const rot = displayRotationForMap(mapId);
  const adjusted = playerMarkerHeading(mapId, heading);
  const imgRot = rot ? adjusted - rot : adjusted;
  return `rotate(${imgRot}deg)`;
}

function renderPlayerOverlay() {
  if (!playerOverlay) {
    return;
  }
  const gen = state.overlayGeneration;
  playerOverlay.replaceChildren();
  const loc = state.playerLocation;
  const showDefault = !loc?.valid;
  const effectiveLoc = loc?.valid
    ? loc
    : { valid: true, x: 0, y: 0, z: 0, rotation: 0 };
  const mapId = state.currentId;
  if (!state.showPlayer) {
    return;
  }
  const meta = isDevPointSource()
    ? pointMetaForMap(mapId) || state.mapMeta?.[mapId]
    : state.mapMeta?.[mapId];
  const { iw, ih } = mapDimensions();
  const ready = isEftarkovPointSource()
    ? Boolean(comPlayerOverlayReady(mapId) && iw && ih)
    : Boolean(meta && iw && ih);
  if (gen !== state.overlayGeneration || mapId !== state.currentId || !ready) {
    return;
  }
  const pos = gameToPlayerMapPixels(
    Number(effectiveLoc.x),
    Number(effectiveLoc.z),
    meta || state.mapMeta?.[mapId],
    iw,
    ih,
    mapId
  );
  if (!pos) {
    return;
  }
  const heading = Number(effectiveLoc.rotation) || 0;
  const marker = document.createElement("div");
  marker.className = "player-marker";
  if (showDefault) {
    marker.classList.add("player-marker-default");
  }
  marker.id = "player-self";
  marker.style.left = `${(pos.x / iw) * 100}%`;
  marker.style.top = `${(pos.y / ih) * 100}%`;
  marker.style.width = `${PLAYER_MARKER_SIZE}px`;
  marker.style.height = `${PLAYER_MARKER_SIZE}px`;
  marker.style.transform = "translate(-50%, -50%)";

  const img = document.createElement("img");
  img.src = playerIconURL();
  img.alt = "player";
  img.draggable = false;
  img.style.transform = playerMarkerRotation(mapId, heading);
  marker.appendChild(img);
  appendMarkerCoordsLabel(marker, Number(effectiveLoc.x), Number(effectiveLoc.z));
  if (gen !== state.overlayGeneration) {
    return;
  }
  playerOverlay.appendChild(marker);
  syncMarkerLabelVisibility();
}

const SATELLITE_OVERLAY_MAPS = new Set([]);

const SATELLITE_OVERLAY_OPACITY_DEFAULT = 0.72;

const DEV_MAP_SVG_LAYERS = {
  interchange: {
    layerIds: ["Ground_Level", "First_Floor", "Second_Floor"],
    hideGroups: ["Ground_Level", "Second_Floor"],
    hideGroupsByVariant: {
      A: ["Ground_Level", "Second_Floor"],
      B: ["Second_Floor"],
    },
    hideWithin: {
      Ground_Level: ["Structure"],
    },
  },
  factory: {
    layerIds: ["Basement", "Ground_Floor", "Second_Floor", "Third_Floor"],
    layerOpacity: {
      Basement: 0.5,
    },
    hideGroups: ["Basement", "Third_Floor"],
    hideGroupsByVariant: {
      A: ["Basement", "Third_Floor"],
      B: ["Third_Floor"],
    },
  },
  reserve: {
    layerIds: ["Ground_Level", "Bunkers"],
    hideGroups: ["Bunkers"],
  },
};

function satelliteOverlayRect(mapId = state.currentId) {
  const meta = state.mapMeta?.[mapId];
  if (!meta) {
    return null;
  }
  const width = Number(meta.overlay_width);
  const height = Number(meta.overlay_height);
  if (!(width > 0 && height > 0)) {
    return null;
  }
  const opacity = Number(meta.overlay_opacity);
  return {
    left: Number(meta.overlay_left) || 0,
    top: Number(meta.overlay_top) || 0,
    width,
    height,
    opacity:
      Number.isFinite(opacity) && opacity > 0 && opacity <= 1
        ? opacity
        : SATELLITE_OVERLAY_OPACITY_DEFAULT,
  };
}

function resetMapInlineLayout() {
  if (!mapInline) {
    return;
  }
  mapInline.style.left = "0";
  mapInline.style.top = "0";
  mapInline.style.width = "100%";
  mapInline.style.height = "100%";
  mapInline.style.opacity = "";
}

function applySatelliteOverlayLayout(mapId = state.currentId) {
  resetMapInlineLayout();
  if (!usesSatelliteOverlay(mapId)) {
    return;
  }
  if (mapId === "interchange") {
    mapInline.style.left = "0";
    mapInline.style.top = "0";
    mapInline.style.width = "100%";
    mapInline.style.height = "100%";
    mapInline.style.opacity = "1";
    return;
  }
  const rect = satelliteOverlayRect(mapId);
  const { iw, ih } = mapDimensions();
  if (!rect || !iw || !ih) {
    return;
  }
  mapInline.style.left = `${(rect.left / iw) * 100}%`;
  mapInline.style.top = `${(rect.top / ih) * 100}%`;
  mapInline.style.width = `${(rect.width / iw) * 100}%`;
  mapInline.style.height = `${(rect.height / ih) * 100}%`;
  mapInline.style.opacity = String(rect.opacity);
}

function usesSatelliteOverlay(mapId) {
  if (!SATELLITE_OVERLAY_MAPS.has(mapId) || !isDevPointSource()) {
    return false;
  }
  if (mapId === "interchange" && devMapVariant() === "B") {
    return false;
  }
  if (mapId === "factory" && devMapVariant() === "B") {
    return false;
  }
  return true;
}

function mapOverlayUrl(mapId) {
  if (!usesSatelliteOverlay(mapId)) {
    return null;
  }
  return `/api/map/${encodeURIComponent(mapId)}/overlay?${mapSourceQuery()}`;
}

function mountMapOverlaySvg(svg, mapId) {
  if (!svg) {
    return;
  }
  svg.setAttribute("focusable", "false");
  svg.style.display = "block";
  svg.style.pointerEvents = "none";
  svg.setAttribute("preserveAspectRatio", "none");
  applyMapSvgLayers(svg, mapId);
  applySatelliteOverlayLayout(mapId);
}

function showRasterWithOverlay() {
  hideAllMapLayers();
  mapImage.classList.remove("hidden");
  mapInline.classList.remove("hidden");
  mapInline.removeAttribute("aria-hidden");
}

function setSvgElementVisible(el, visible) {
  if (!el) {
    return;
  }
  el.style.display = visible ? "" : "none";
}

function devMapSvgLayerConfig(mapId) {
  const cfg = DEV_MAP_SVG_LAYERS[mapId];
  if (!cfg) {
    return null;
  }
  if (cfg.hideGroupsByVariant && isDevPointSource()) {
    const variant = devMapVariant();
    const hideGroups = cfg.hideGroupsByVariant[variant] ?? cfg.hideGroups;
    return { ...cfg, hideGroups };
  }
  return cfg;
}

function applyMapSvgLayers(svg, mapId) {
  if (!svg || !mapId) {
    return;
  }
  const cfg = devMapSvgLayerConfig(mapId);
  if (!cfg) {
    return;
  }
  const layerIds = cfg.layerIds || ["Ground_Level", "First_Floor", "Second_Floor"];
  for (const id of layerIds) {
    const el = svg.querySelector(`#${id}`);
    if (!el) {
      continue;
    }
    setSvgElementVisible(el, !cfg.hideGroups?.includes(id));
    const opacity = cfg.layerOpacity?.[id];
    if (opacity != null) {
      el.style.opacity = String(opacity);
    } else {
      el.style.removeProperty("opacity");
    }
  }
  if (cfg.hideWithin) {
    for (const [parentId, childIds] of Object.entries(cfg.hideWithin)) {
      const parent = svg.querySelector(`#${parentId}`);
      if (!parent) {
        continue;
      }
      for (const childId of childIds) {
        setSvgElementVisible(parent.querySelector(`#${childId}`), false);
      }
    }
  }
}

function hideAllMapLayers() {
  mapInline.classList.add("hidden");
  mapInline.setAttribute("aria-hidden", "true");
  mapImage.classList.add("hidden");
}

function activeMapNode() {
  if (mapInline && !mapInline.classList.contains("hidden")) {
    return mapInline.querySelector("svg");
  }
  if (mapImage && !mapImage.classList.contains("hidden")) {
    return mapImage;
  }
  return null;
}

function resetMapDisplayForLoad() {
  hideAllMapLayers();
  mapInline.innerHTML = "";
  resetMapInlineLayout();
  mapImage.removeAttribute("src");
  state.mapWidth = 0;
  state.mapHeight = 0;
  if (mapContent) {
    mapContent.style.width = "";
    mapContent.style.height = "";
    mapContent.style.transform = "";
  }
}

function showInlineMap() {
  hideAllMapLayers();
  mapInline.classList.remove("hidden");
  mapInline.removeAttribute("aria-hidden");
  mapImage.removeAttribute("src");
}

function showRasterMap() {
  hideAllMapLayers();
  mapInline.innerHTML = "";
  resetMapInlineLayout();
  mapImage.classList.remove("hidden");
}

function mapDisplayRotation() {
  return displayRotationForMap(state.currentId);
}

function rotatedLayoutSize(width, height, degrees) {
  if (!degrees || !width || !height) {
    return { width, height };
  }
  const rad = (Math.abs(degrees) * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return {
    width: width * cos + height * sin,
    height: width * sin + height * cos,
  };
}

function currentMapEntry() {
  return state.maps.find((m) => m.id === state.currentId) || null;
}

function applyMapDimensionsFromEntry(entry, mapId = entry?.id) {
  if (!mapId) {
    return;
  }
  const meta = state.mapMeta?.[mapId];
  const w = Number(meta?.width) || Number(entry?.width) || 0;
  const h = Number(meta?.height) || Number(entry?.height) || 0;
  if (w > 0) {
    state.mapWidth = w;
    if (entry) {
      entry.width = w;
    }
  }
  if (h > 0) {
    state.mapHeight = h;
    if (entry) {
      entry.height = h;
    }
  }
}

function eftarkovDisplayDimensions(mapId = state.currentId) {
  const meta = state.mapMeta?.[mapId];
  const w = Number(meta?.width) || 0;
  const h = Number(meta?.height) || 0;
  if (w > 0 && h > 0) {
    return { iw: w, ih: h };
  }
  const entry = state.maps.find((m) => m.id === mapId);
  const ew = Number(entry?.width) || 0;
  const eh = Number(entry?.height) || 0;
  if (ew > 0 && eh > 0) {
    return { iw: ew, ih: eh };
  }
  return null;
}

function syncRasterMapDimensions() {
  if (isEftarkovPointSource()) {
    const dims = eftarkovDisplayDimensions();
    if (dims) {
      state.mapWidth = dims.iw;
      state.mapHeight = dims.ih;
      const entry = currentMapEntry();
      if (entry) {
        entry.width = dims.iw;
        entry.height = dims.ih;
      }
      return true;
    }
  }
  if (isDevPointSource()) {
    const { iw, ih } = mapDimensions();
    if (iw > 0 && ih > 0) {
      state.mapWidth = iw;
      state.mapHeight = ih;
      const entry = currentMapEntry();
      if (entry) {
        entry.width = iw;
        entry.height = ih;
      }
      return true;
    }
  }
  if (!mapImage || mapImage.classList.contains("hidden")) {
    return false;
  }
  const nw = mapImage.naturalWidth || 0;
  const nh = mapImage.naturalHeight || 0;
  if (nw <= 0 || nh <= 0) {
    return false;
  }
  state.mapWidth = nw;
  state.mapHeight = nh;
  const entry = currentMapEntry();
  if (entry) {
    entry.width = nw;
    entry.height = nh;
  }
  return true;
}

function viewFitKey() {
  const variantPart = isDevPointSource() ? `:${devMapVariant()}` : "";
  return `${state.pointSource}${variantPart}:${state.currentId}:${state.mapWidth}x${state.mapHeight}`;
}

function finalizeMapViewport(loadToken = state.mapLoadToken) {
  if (loadToken !== state.mapLoadToken) {
    return false;
  }
  const entry = currentMapEntry();
  if (!syncRasterMapDimensions()) {
    if (!entry) {
      return false;
    }
    applyMapDimensionsFromEntry(entry);
  }
  if (!state.mapWidth || !state.mapHeight) {
    return false;
  }
  state.tx = 0;
  state.ty = 0;
  const fitted = fitMapToView();
  if (!fitted) {
    const { iw, ih } = mapDimensions();
    if (mapContent && iw > 0 && ih > 0) {
      if (state.scale <= 0) {
        state.baseScale = 1;
        state.scale = defaultScale();
      }
      applyTransform();
    }
  } else {
    state.viewFitKey = viewFitKey();
  }
  refreshPointOverlays(loadToken);
  applySatelliteOverlayLayout(state.currentId);
  return fitted || Boolean(state.mapWidth && state.mapHeight);
}

function minZoomRatioForEntry(entry) {
  const mapId = entry?.id;
  if (isEftarkovPointSource()) {
    if (mapId && COM_MAP_MIN_ZOOM_RATIO[mapId] != null) {
      return COM_MAP_MIN_ZOOM_RATIO[mapId];
    }
    return MIN_ZOOM_RATIO;
  }
  if (mapId && MAP_MIN_ZOOM_RATIO[mapId] != null) {
    return MAP_MIN_ZOOM_RATIO[mapId];
  }
  return MIN_ZOOM_RATIO;
}

function applyTransform() {
  const { iw, ih } = mapDimensions();
  const rot = mapDisplayRotation();
  const rotatePart = rot ? ` rotate(${rot}deg)` : "";

  if (mapContent && iw > 0 && ih > 0 && state.scale > 0) {
    mapContent.style.width = `${iw * state.scale}px`;
    mapContent.style.height = `${ih * state.scale}px`;
    mapContent.style.transformOrigin = "center center";
    mapContent.style.transform = rotatePart;
  }

  const node = activeMapNode();
  if (node) {
    node.style.width = "100%";
    node.style.height = "100%";
  }

  stage.style.transform = `translate(calc(-50% + ${state.tx}px), calc(-50% + ${state.ty}px))`;
}

function mapDimensions() {
  if (isEftarkovPointSource()) {
    const dims = eftarkovDisplayDimensions();
    if (dims) {
      return dims;
    }
  }
  if (isDevPointSource()) {
    const displayMeta = devDisplayMeta();
    const mw = Number(displayMeta?.width) || 0;
    const mh = Number(displayMeta?.height) || 0;
    if (mw > 0 && mh > 0) {
      return { iw: mw, ih: mh };
    }
    const nw = mapImage?.naturalWidth || 0;
    const nh = mapImage?.naturalHeight || 0;
    if (nw > 0 && nh > 0 && mapImage && !mapImage.classList.contains("hidden")) {
      return { iw: nw, ih: nh };
    }
  }
  return { iw: state.mapWidth || 0, ih: state.mapHeight || 0 };
}

function fitMapToView() {
  const vw = viewport.clientWidth;
  const vh = viewport.clientHeight;
  const { iw, ih } = mapDimensions();
  if (!vw || !vh || !iw || !ih) {
    return false;
  }
  const layout = rotatedLayoutSize(iw, ih, mapDisplayRotation());
  const fit = Math.min(vw / layout.width, vh / layout.height);
  state.baseScale = fit;
  state.scale = defaultScale();
  state.tx = 0;
  state.ty = 0;
  applyTransform();
  state.viewFitKey = viewFitKey();
  return true;
}

function resetView() {
  fitMapToView();
  applyPlayerCenterLock();
}

function onViewportResize() {
  const { iw, ih } = mapDimensions();
  if (iw <= 0 || ih <= 0) {
    return;
  }
  const preserveZoom = state.viewFitKey === viewFitKey();
  const zoomRatio = preserveZoom && state.baseScale > 0 ? state.scale / state.baseScale : 1;
  if (!fitMapToView()) {
    return;
  }
  if (preserveZoom) {
    state.scale = clampScale(state.baseScale * zoomRatio);
  }
  state.tx = 0;
  state.ty = 0;
  applyTransform();
  applyPlayerCenterLock();
}

const MIN_ZOOM_RATIO = 0.9;

function defaultScale() {
  return state.baseScale * minZoomRatioForEntry(currentMapEntry());
}

function clampScale(value) {
  const min = defaultScale();
  const max = state.baseScale * 6;
  return Math.min(max, Math.max(min, value));
}

function showCachedMap(entry, cached) {
  mapInline.innerHTML = "";
  mapImage.removeAttribute("src");

  if (cached.kind === "rasterOverlay") {
    showRasterWithOverlay();
    mapImage.alt = entry.displayName;
    mapImage.src = cached.imageSrc || cached.blobUrl;
    mapInline.innerHTML = cached.overlayText;
    mountMapOverlaySvg(mapInline.querySelector("svg"), entry.id);
    return loadRasterImageSoft(mapImage);
  }

  if (cached.kind === "raster") {
    showRasterMap();
    mapImage.alt = entry.displayName;
    mapImage.src = cached.imageSrc || cached.blobUrl;
    return loadRasterImageSoft(mapImage);
  }

  showInlineMap();
  mapInline.innerHTML = cached.text;
  const svg = mapInline.querySelector("svg");
  if (!svg) {
    throw new Error("svg");
  }
  svg.setAttribute("focusable", "false");
  svg.style.display = "block";
  svg.style.pointerEvents = "none";
  applyMapSvgLayers(svg, entry.id);
  return Promise.resolve();
}

async function loadMapImage(entry) {
  const token = ++state.mapLoadToken;
  if (isEftarkovPointSource()) {
    try {
      await ensureComPointData();
    } catch {
    }
  }
  invalidateOverlays();
  state.tx = 0;
  state.ty = 0;
  state.viewFitKey = "";
  resetMapDisplayForLoad();

  const latestEntry = state.maps.find((m) => m.id === entry.id) || entry;
  entry = latestEntry;

  invalidateMapContentCacheIfStale(entry.id);
  const assetRev = mapAssetRevision(entry.id);
  const cached = mapContentCache.get(mapCacheKey(entry.id));
  if (cached && (!assetRev || cached.rev === assetRev)) {
    try {
      await showCachedMap(entry, cached);
      if (token !== state.mapLoadToken) {
        clearPointOverlays();
        return;
      }
      scheduleFitMapToView(token);
    } catch {
      mapContentCache.delete(mapCacheKey(entry.id));
      if (token === state.mapLoadToken) {
        loadMapImage(entry);
      }
    }
    return;
  }

  const url = mapFetchUrl(entry);

  try {
    const res = await fetch(url, { cache: "no-store" });
    if (token !== state.mapLoadToken) {
      clearPointOverlays();
      return;
    }
    if (!res.ok) {
      throw new Error(String(res.status));
    }

    const servedId = (res.headers.get("X-Map-Id") || "").toLowerCase();
    if (servedId && servedId !== entry.id) {
      throw new Error(`map-id-mismatch:${servedId}`);
    }

    const contentType = res.headers.get("Content-Type") || "";

    if (isRasterMapContentType(contentType)) {
      if (canLoadRasterDirect(entry.id, entry)) {
        if (token !== state.mapLoadToken) {
          clearPointOverlays();
          return;
        }
        mapContentCache.set(mapCacheKey(entry.id), {
          kind: "raster",
          imageSrc: url,
          blobUrl: null,
          rev: assetRev,
        });
        showRasterMap();
        mapImage.alt = entry.displayName;
        mapImage.src = url;
        await loadRasterImageSoft(mapImage);
        if (token !== state.mapLoadToken) {
          clearPointOverlays();
          return;
        }
        scheduleFitMapToView(token);
        return;
      }

      const blob = await res.blob();
      if (token !== state.mapLoadToken) {
        clearPointOverlays();
        return;
      }
      const { imageSrc, blobUrl } = await resolveRasterDisplaySrc(url, blob);
      const overlayUrl = mapOverlayFetchUrl(entry.id);
      let overlayText = null;
      if (overlayUrl) {
        const overlayRes = await fetch(overlayUrl, { cache: "no-store" });
        if (token !== state.mapLoadToken) {
          clearPointOverlays();
          return;
        }
        if (overlayRes.ok) {
          overlayText = await overlayRes.text();
        }
      }
      if (token !== state.mapLoadToken) {
        clearPointOverlays();
        return;
      }
      const rasterCache = {
        imageSrc,
        blobUrl,
        rev: assetRev,
      };
      if (overlayText) {
        mapContentCache.set(mapCacheKey(entry.id), {
          kind: "rasterOverlay",
          ...rasterCache,
          overlayText,
        });
        showRasterWithOverlay();
      } else {
        mapContentCache.set(mapCacheKey(entry.id), { kind: "raster", ...rasterCache });
        showRasterMap();
      }
      mapImage.alt = entry.displayName;
      mapImage.src = imageSrc;
      await loadRasterImageSoft(mapImage);
      if (token !== state.mapLoadToken) {
        clearPointOverlays();
        return;
      }
      if (overlayText) {
        mapInline.innerHTML = overlayText;
        mountMapOverlaySvg(mapInline.querySelector("svg"), entry.id);
      }
    } else {
      const text = await res.text();
      if (token !== state.mapLoadToken) {
        clearPointOverlays();
        return;
      }
      mapContentCache.set(mapCacheKey(entry.id), { kind: "svg", text });
      showInlineMap();
      mapInline.innerHTML = text;
      const svg = mapInline.querySelector("svg");
      if (!svg) {
        throw new Error("svg");
      }
      svg.setAttribute("focusable", "false");
      svg.style.display = "block";
      svg.style.pointerEvents = "none";
      applyMapSvgLayers(svg, entry.id);
    }

    scheduleFitMapToView(token);
  } catch {
    if (token !== state.mapLoadToken) {
      clearPointOverlays();
      return;
    }
    applyMapDimensionsFromEntry(entry, entry.id);
    showRasterMap();
    mapImage.alt = t("map_load_error", "MAP LOAD ERROR");
    if (state.mapWidth > 0 && state.mapHeight > 0) {
      scheduleFitMapToView(token);
    } else {
      clearPointOverlays();
    }
  }
}

function refreshMapLabels() {
  for (const map of state.maps) {
    map.displayName = mapLabel(map.id, map.fallbackName || map.id);
  }
  updateSelectLabel();
  renderDropdown();
}

function updateSelectLabel() {
  if (state.catalogError) {
    setSelectErrorLabel();
    return;
  }
  const entry = state.maps.find((m) => m.id === state.currentId);
  const fallback = t("select_map", "SELECT MAP");
  const label = entry ? entry.displayName : fallback;
  selectBtn.innerHTML = `${label}<span class="select-caret" aria-hidden="true">▼</span>`;
}

function setSelectErrorLabel() {
  state.catalogError = true;
  const label = t("map_error", "MAP ERROR");
  selectBtn.innerHTML = `${label}<span class="select-caret" aria-hidden="true">▼</span>`;
}

function setMap(id) {
  const entry = state.maps.find((m) => m.id === id) || state.maps[0];
  if (!entry) {
    return;
  }
  state.currentId = entry.id;
  localStorage.setItem(STORAGE_KEY, entry.id);
  mapImage.alt = entry.displayName;
  updateSelectLabel();
  refreshExfilFilterVisibility();
  dropdown.querySelectorAll(".dropdown-option").forEach((el) => {
    el.classList.toggle("is-active", el.dataset.mapId === entry.id);
  });
  loadMapImage(entry);
  pushEmbeddedContext();
}

function closeDropdown() {
  dropdown.classList.add("hidden");
  selectBtn.setAttribute("aria-expanded", "false");
}

function openDropdown() {
  dropdown.classList.remove("hidden");
  selectBtn.setAttribute("aria-expanded", "true");
}

function toggleDropdown() {
  if (dropdown.classList.contains("hidden")) {
    closePointsPanel();
    closeEmbeddedPanel();
    openDropdown();
  } else {
    closeDropdown();
  }
}

function closePointsPanel() {
  if (!pointsPanel) {
    return;
  }
  pointsPanel.classList.add("hidden");
  if (pointsSelectBtn) {
    pointsSelectBtn.setAttribute("aria-expanded", "false");
  }
}

function openPointsPanel() {
  if (!pointsPanel) {
    return;
  }
  pointsPanel.classList.remove("hidden");
  if (pointsSelectBtn) {
    pointsSelectBtn.setAttribute("aria-expanded", "true");
  }
}

function togglePointsPanel() {
  if (!pointsPanel) {
    return;
  }
  if (pointsPanel.classList.contains("hidden")) {
    closeDropdown();
    closeLangDropdown();
    closeEmbeddedPanel();
    openPointsPanel();
  } else {
    closePointsPanel();
  }
}

function closeEmbeddedPanel() {
  if (!embeddedPanel) {
    return;
  }
  embeddedPanel.classList.add("hidden");
  if (embeddedSelectBtn) {
    embeddedSelectBtn.setAttribute("aria-expanded", "false");
  }
  syncEmbeddedStatusPolling();
}

function openEmbeddedPanel() {
  if (!embeddedPanel) {
    return;
  }
  embeddedPanel.classList.remove("hidden");
  if (embeddedSelectBtn) {
    embeddedSelectBtn.setAttribute("aria-expanded", "true");
  }
  syncEmbeddedStatusPolling();
}

function toggleEmbeddedPanel() {
  if (!embeddedPanel) {
    return;
  }
  if (embeddedPanel.classList.contains("hidden")) {
    closeDropdown();
    closeLangDropdown();
    closePointsPanel();
    openEmbeddedPanel();
  } else {
    closeEmbeddedPanel();
  }
}

function closeLangDropdown() {
  if (!langDropdown) {
    return;
  }
  langDropdown.classList.add("hidden");
  if (langSelectBtn) {
    langSelectBtn.setAttribute("aria-expanded", "false");
  }
}

function openLangDropdown() {
  if (!langDropdown) {
    return;
  }
  langDropdown.classList.remove("hidden");
  if (langSelectBtn) {
    langSelectBtn.setAttribute("aria-expanded", "true");
  }
}

function toggleLangDropdown() {
  if (!langDropdown) {
    return;
  }
  if (langDropdown.classList.contains("hidden")) {
    closeDropdown();
    closePointsPanel();
    closeEmbeddedPanel();
    openLangDropdown();
  } else {
    closeLangDropdown();
  }
}

function renderLangDropdown() {
  if (!langDropdown) {
    return;
  }
  langDropdown.innerHTML = "";
  const order = state.locale.order || [];
  for (const code of order) {
    const label = (state.locale.labels && state.locale.labels[code]) || code;
    const item = document.createElement("div");
    item.className = "dropdown-option lang-option";
    item.dataset.locale = code;
    item.setAttribute("role", "option");
    item.textContent = label;
    if (code === state.locale.code) {
      item.classList.add("is-active");
    }
    item.addEventListener("mousedown", (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
    item.addEventListener("click", (e) => {
      e.stopPropagation();
      if (code !== state.locale.code) {
        setLocale(code);
      }
      closeLangDropdown();
    });
    langDropdown.appendChild(item);
  }
}

function renderDropdown() {
  dropdown.innerHTML = "";
  for (const map of state.maps) {
    const item = document.createElement("div");
    item.className = "dropdown-option";
    item.dataset.mapId = map.id;
    item.setAttribute("role", "option");
    item.textContent = map.displayName;
    if (map.id === state.currentId) {
      item.classList.add("is-active");
    }
    item.addEventListener("mousedown", (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
    item.addEventListener("click", (e) => {
      e.stopPropagation();
      setMap(map.id);
      closeDropdown();
    });
    dropdown.appendChild(item);
  }
}

function defaultMapId() {
  const id = String(state.catalogDefaultMap || DEFAULT_MAP).toLowerCase();
  return id || DEFAULT_MAP;
}

function pickInitialMap() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && state.maps.some((m) => m.id === saved)) {
    return saved;
  }
  const def = defaultMapId();
  if (state.maps.some((m) => m.id === def)) {
    return def;
  }
  return state.maps[0]?.id || def;
}

async function reloadMapCatalog() {
  const res = await fetch(`/api/maps?${mapSourceQuery()}`);
  if (!res.ok) {
    throw new Error("maps");
  }
  const contentType = (res.headers.get("Content-Type") || "").toLowerCase();
  if (!contentType.includes("application/json")) {
    throw new Error("maps");
  }
  const items = await res.json();
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error("maps-empty");
  }
  const catalogDefault = (res.headers.get("X-Map-Default") || "").trim().toLowerCase();
  if (catalogDefault) {
    state.catalogDefaultMap = catalogDefault;
  }
  state.catalogError = false;
  state.maps = items.map((item) => ({
    id: item.id,
    displayName: item.displayName,
    fallbackName: item.displayName,
    svgUrl: item.svgUrl,
    width: item.width,
    height: item.height,
  }));
  refreshMapLabels();
  renderDropdown();
  updateSelectLabel();
}

async function loadCatalog() {
  await reloadMapCatalog();
  const saved = localStorage.getItem(STORAGE_KEY);
  const nextId =
    saved && state.maps.some((m) => m.id === saved)
      ? saved
      : pickInitialMap();
  setMap(nextId);
}

function scheduleFitMapToView(loadToken = state.mapLoadToken) {
  let attempts = 0;
  const tick = () => {
    if (loadToken !== state.mapLoadToken) {
      return;
    }
    attempts += 1;
    if (finalizeMapViewport(loadToken)) {
      return;
    }
    if (attempts < 12) {
      requestAnimationFrame(tick);
    } else {
      refreshPointOverlays(loadToken);
    }
  };
  if (!finalizeMapViewport(loadToken)) {
    requestAnimationFrame(tick);
  }
}

selectBtn.addEventListener("mousedown", (e) => {
  e.stopPropagation();
});

selectBtn.addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  closeLangDropdown();
  toggleDropdown();
});

if (pointsSelectBtn) {
  pointsSelectBtn.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  pointsSelectBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    closeDropdown();
    closeLangDropdown();
    togglePointsPanel();
  });
}

document.addEventListener("mousedown", (e) => {
  if (selectRoot && !selectRoot.contains(e.target)) {
    closeDropdown();
  }
  if (pointsSelectRoot && !pointsSelectRoot.contains(e.target)) {
    closePointsPanel();
  }
  if (embeddedSelectRoot && !embeddedSelectRoot.contains(e.target)) {
    closeEmbeddedPanel();
  }
  if (langSelectRoot && !langSelectRoot.contains(e.target)) {
    closeLangDropdown();
  }
});

resetBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  resetView();
});

if (langSelectBtn) {
  langSelectBtn.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  langSelectBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    closeDropdown();
    toggleLangDropdown();
  });
}

viewport.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    state.scale = clampScale(state.scale * delta);
    applyTransform();
    applyPlayerCenterLock();
  },
  { passive: false }
);

viewport.addEventListener("mousedown", (e) => {
  if (e.button !== 0) {
    return;
  }
  if (state.playerCenterLock) {
    return;
  }
  state.dragging = true;
  state.dragStartX = e.clientX;
  state.dragStartY = e.clientY;
  state.panStartX = state.tx;
  state.panStartY = state.ty;
  viewport.classList.add("is-dragging");
});

window.addEventListener("mousemove", (e) => {
  if (!state.dragging || state.playerCenterLock) {
    return;
  }
  state.tx = state.panStartX + (e.clientX - state.dragStartX);
  state.ty = state.panStartY + (e.clientY - state.dragStartY);
  applyTransform();
  scheduleMouseCoordsUpdate(e.clientX, e.clientY);
});

viewport.addEventListener("mousemove", (e) => {
  scheduleMouseCoordsUpdate(e.clientX, e.clientY);
});

viewport.addEventListener("mouseleave", () => {
  clearMouseCoordsDisplay();
});

window.addEventListener("mouseup", () => {
  state.dragging = false;
  viewport.classList.remove("is-dragging");
});

window.addEventListener("resize", onViewportResize);

if (typeof ResizeObserver !== "undefined" && viewport) {
  const viewportObserver = new ResizeObserver(() => {
    onViewportResize();
  });
  viewportObserver.observe(viewport);
}

async function pollPlayerLocation() {
  try {
    const res = await fetch("/api/player/self");
    if (!res.ok) {
      return;
    }
    state.playerLocation = await res.json();
    refreshPointOverlays();
  } catch {
  }
}

function startPlayerPoll() {
  pollPlayerLocation();
  window.setInterval(pollPlayerLocation, 400);
}

async function init() {
  await loadLocale();
  refreshPointSourceLabel();
  await loadEmbeddedSettings();
  try {
    await Promise.allSettled([
      loadMapMeta(),
      loadTarkovDevMeta(),
      loadTarkovDevMetaB(),
      loadEftarkovMeta(),
      loadExfilData(),
    ]);
  } catch {
  }
  try {
    await loadCatalog();
    refreshExfilFilterVisibility();
    startPlayerPoll();
    if (state.embeddedPosition !== "none") {
      await pushEmbeddedSettings();
    }
  } catch {
    setSelectErrorLabel();
  }
}

if (pointSourceBtn) {
  pointSourceBtn.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  pointSourceBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    cyclePointSource();
  });
}

for (const { kind } of EXFIL_KINDS) {
  const input = document.getElementById(`exfil-filter-${kind}`);
  if (!input) {
    continue;
  }
  input.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  input.addEventListener("change", () => {
    state.exfilFilters[kind] = input.checked;
    syncExfilGroupCheckbox();
    refreshPointOverlays();
  });
}

if (exfilGroupToggle) {
  exfilGroupToggle.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  exfilGroupToggle.addEventListener("change", () => {
    const on = exfilGroupToggle.checked;
    for (const kind of visibleExfilKinds()) {
      state.exfilFilters[kind] = on;
      const el = document.getElementById(`exfil-filter-${kind}`);
      if (el) {
        el.checked = on;
      }
    }
    syncExfilGroupCheckbox();
    refreshPointOverlays();
  });
}

if (exfilPmcNamesToggle) {
  exfilPmcNamesToggle.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  exfilPmcNamesToggle.addEventListener("change", () => {
    state.exfilShowNames = exfilPmcNamesToggle.checked;
    syncMarkerLabelVisibility();
  });
}

if (exfilShowCoordsToggle) {
  exfilShowCoordsToggle.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  exfilShowCoordsToggle.addEventListener("change", () => {
    state.showMarkerCoords = exfilShowCoordsToggle.checked;
    syncMarkerLabelVisibility();
  });
}

if (exfilPlayerToggle) {
  exfilPlayerToggle.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  exfilPlayerToggle.addEventListener("change", () => {
    state.showPlayer = exfilPlayerToggle.checked;
    refreshPointOverlays();
  });
}

if (exfilPlayerLockToggle) {
  exfilPlayerLockToggle.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  exfilPlayerLockToggle.addEventListener("change", () => {
    if (!exfilPlayerLockToggle.checked && state.embeddedPosition !== "none") {
      state.embeddedPosition = "none";
      syncEmbeddedControlsFromState();
      pushEmbeddedSettings();
      return;
    }
    state.playerCenterLock = exfilPlayerLockToggle.checked;
    applyPlayerCenterLock();
  });
}

function bindEmbeddedSelect(selectEl) {
  if (!selectEl) {
    return;
  }
  selectEl.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  selectEl.addEventListener("change", (e) => {
    e.stopPropagation();
    pushEmbeddedSettings();
  });
}

bindEmbeddedSelect(embeddedPositionSelect);
bindEmbeddedSelect(embeddedRangeSelect);
bindEmbeddedSelect(embeddedSizeSelect);
bindEmbeddedSelect(embeddedOffsetXSelect);
bindEmbeddedSelect(embeddedOffsetYSelect);
bindEmbeddedSelect(embeddedOpacitySelect);

if (embeddedSelectBtn) {
  embeddedSelectBtn.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
  embeddedSelectBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleEmbeddedPanel();
  });
}

if (embeddedPanel) {
  embeddedPanel.addEventListener("mousedown", (e) => {
    e.stopPropagation();
  });
}

document.addEventListener("contextmenu", (event) => {
  event.preventDefault();
});

init();
