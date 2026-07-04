package maps

import (
	"io/fs"
	"net/http"
	"path"
	"strings"
)

type Meta struct {
	Name                string    `json:"name"`
	DisplayName         string    `json:"display_name"`
	Description         string    `json:"description"`
	XMin                float64   `json:"xmin"`
	XMax                float64   `json:"xmax"`
	ZMin                float64   `json:"zmin"`
	ZMax                float64   `json:"zmax"`
	CoordinatesRotation int       `json:"coordinates_rotation"`
	DisplayRotation     int       `json:"display_rotation,omitempty"`
	Width               float64   `json:"width,omitempty"`
	Height              float64   `json:"height,omitempty"`
	StitchWidth         float64   `json:"stitch_width,omitempty"`
	StitchHeight        float64   `json:"stitch_height,omitempty"`
	MapOffsetX          float64   `json:"map_offset_x,omitempty"`
	MapOffsetY          float64   `json:"map_offset_y,omitempty"`
	TileZoom            int       `json:"tile_zoom,omitempty"`
	TileMinX            int       `json:"tile_min_x,omitempty"`
	TileMinY            int       `json:"tile_min_y,omitempty"`
	TileMaxX            int       `json:"tile_max_x,omitempty"`
	TileMaxY            int       `json:"tile_max_y,omitempty"`
	TileSize            int       `json:"tile_size,omitempty"`
	Transform           []float64 `json:"transform,omitempty"`
	SvgXMin             float64   `json:"svg_xmin,omitempty"`
	SvgXMax             float64   `json:"svg_xmax,omitempty"`
	SvgZMin             float64   `json:"svg_zmin,omitempty"`
	SvgZMax             float64   `json:"svg_zmax,omitempty"`
	MapAssetRev         string    `json:"map_asset_rev,omitempty"`
	OverlayLeft         float64   `json:"overlay_left,omitempty"`
	OverlayTop          float64   `json:"overlay_top,omitempty"`
	OverlayWidth        float64   `json:"overlay_width,omitempty"`
	OverlayHeight       float64   `json:"overlay_height,omitempty"`
	OverlayOpacity      float64   `json:"overlay_opacity,omitempty"`
	EftarkovCols        int       `json:"eftarkov_cols,omitempty"`
	EftarkovRows        int       `json:"eftarkov_rows,omitempty"`
	EftarkovTileSize    int       `json:"eftarkov_tile_size,omitempty"`
}

type Entry struct {
	ID          string  `json:"id"`
	DisplayName string  `json:"displayName"`
	SVGURL      string  `json:"svgUrl"`
	Width       float64 `json:"width"`
	Height      float64 `json:"height"`
}

func RegisterRoutes(mux *http.ServeMux, frontend fs.FS) {
	mux.Handle("/", http.FileServer(http.FS(frontend)))
}

func LoadCatalog(source string) (map[string]Meta, error) {
	st := storeFor(mapRequest{source: source, variant: "A"})
	meta := st.metaByID()
	out := make(map[string]Meta, len(meta))
	for id, rec := range meta {
		out[id] = metaFromRecord(rec)
	}
	return out, nil
}

func ListFor(source string, variant string) ([]Entry, error) {
	st := storeFor(mapRequest{source: source, variant: variant})
	order := st.catalogOrder()
	meta := st.metaByID()
	out := make([]Entry, 0, len(order))
	for _, id := range order {
		rec, ok := meta[id]
		if !ok {
			continue
		}
		if !st.mapExists(id) {
			continue
		}
		name := rec.Name
		if name == "" {
			name = id
		}
		display := rec.DisplayName
		if display == "" {
			display = name
		}
		width, height, _ := mapDimensionsFor(source, variant, id)
		out = append(out, Entry{
			ID:          name,
			DisplayName: display,
			SVGURL:      mapAssetURL(name, source, variant),
			Width:       width,
			Height:      height,
		})
	}
	return out, nil
}

func List() ([]Entry, error) {
	return ListFor("tarkovdev", "A")
}

func MapIDsFor(source string, variant string) []string {
	order := storeFor(mapRequest{source: source, variant: variant}).catalogOrder()
	out := make([]string, len(order))
	copy(out, order)
	return out
}

func MapIDs() []string {
	return MapIDsFor("tarkovdev", "A")
}

func DefaultMapID() string {
	return catalogFallback()
}

func mapAssetURL(id, source, variant string) string {
	if NormalizeSource(source) == "tarkovdev" {
		v := strings.ToLower(NormalizeMapVariant(variant))
		return "/api/map/" + id + "?source=tarkovdev&variant=" + v
	}
	if NormalizeSource(source) == "eftarkov" {
		return "/api/map/" + id + "?source=eftarkov"
	}
	return "/api/map/" + id
}

func SanitizeMapIDFor(source, variant, id string) string {
	return storeFor(mapRequest{source: source, variant: variant}).sanitizeMapID(id)
}

func SanitizeMapID(id string) string {
	return SanitizeMapIDFor("tarkovdev", "A", id)
}

func metaFromRecord(rec metaRecord) Meta {
	return Meta{
		Name:                rec.Name,
		DisplayName:         rec.DisplayName,
		XMin:                rec.XMin,
		XMax:                rec.XMax,
		ZMin:                rec.ZMin,
		ZMax:                rec.ZMax,
		CoordinatesRotation: rec.CoordinatesRotation,
		DisplayRotation:     rec.DisplayRotation,
		Width:               rec.Width,
		Height:              rec.Height,
		MapOffsetX:          rec.MapOffsetX,
		MapOffsetY:          rec.MapOffsetY,
		TileZoom:            rec.TileZoom,
		TileMinX:            rec.TileMinX,
		TileMinY:            rec.TileMinY,
		TileMaxX:            rec.TileMaxX,
		TileMaxY:            rec.TileMaxY,
		TileSize:            rec.TileSize,
		Transform:           rec.Transform,
		SvgXMin:             rec.SvgXMin,
		SvgXMax:             rec.SvgXMax,
		SvgZMin:             rec.SvgZMin,
		SvgZMax:             rec.SvgZMax,
		MapAssetRev:         rec.MapAssetRev,
		EftarkovCols:        rec.EftarkovCols,
		EftarkovRows:        rec.EftarkovRows,
		EftarkovTileSize:    rec.EftarkovTileSize,
	}
}

func mapDimensionsFor(source, variant, mapID string) (width, height float64, ok bool) {
	st := storeFor(mapRequest{source: source, variant: variant})
	rec, found := st.metaByID()[mapID]
	if found && rec.Width > 0 && rec.Height > 0 {
		return rec.Width, rec.Height, true
	}
	data, mime, err := st.mapAsset(mapID)
	if err != nil || mime != "image/svg+xml" {
		return 0, 0, false
	}
	head := data
	if len(head) > 4096 {
		head = head[:4096]
	}
	m := viewBoxRe.FindSubmatch(head)
	if len(m) < 2 {
		return 0, 0, false
	}
	return parseViewBox(string(m[1]))
}

func mapAsset(source, variant, mapID string) ([]byte, string, error) {
	return storeFor(mapRequest{source: source, variant: variant}).mapAsset(mapID)
}

func mapOverlay(source, variant, mapID string) ([]byte, error) {
	return storeFor(mapRequest{source: source, variant: variant}).mapOverlay(mapID)
}

func mapExists(source, variant, mapID string) bool {
	return storeFor(mapRequest{source: source, variant: variant}).mapExists(mapID)
}

func mapSVG(source, variant, mapID string) ([]byte, error) {
	data, mime, err := mapAsset(source, variant, mapID)
	if err != nil {
		return nil, err
	}
	if mime != "image/svg+xml" {
		return nil, fs.ErrNotExist
	}
	return data, nil
}

func serveMapAsset(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	req := mapRequestFromHTTP(r)
	raw := r.PathValue("id")
	if raw == "" {
		raw = path.Base(r.URL.Path)
	}
	id := SanitizeMapIDFor(req.source, req.variant, raw)
	data, mime, err := mapAsset(req.source, req.variant, id)
	if err != nil || len(data) == 0 {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", mime)
	w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
	w.Header().Set("X-Map-Id", id)
	w.Header().Set("X-Map-Source", NormalizeSource(req.source))
	if NormalizeSource(req.source) == "tarkovdev" {
		w.Header().Set("X-Map-Variant", NormalizeMapVariant(req.variant))
	}
	_, _ = w.Write(data)
}

func serveMapOverlay(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	req := mapRequestFromHTTP(r)
	raw := r.PathValue("id")
	if raw == "" {
		raw = path.Base(r.URL.Path)
	}
	id := SanitizeMapIDFor(req.source, req.variant, raw)
	data, err := mapOverlay(req.source, req.variant, id)
	if err != nil || len(data) == 0 {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "image/svg+xml")
	w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
	w.Header().Set("X-Map-Id", id)
	w.Header().Set("X-Map-Source", NormalizeSource(req.source))
	if NormalizeSource(req.source) == "tarkovdev" {
		w.Header().Set("X-Map-Variant", NormalizeMapVariant(req.variant))
	}
	_, _ = w.Write(data)
}
