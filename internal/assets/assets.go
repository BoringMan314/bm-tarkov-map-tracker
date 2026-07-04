package assets

import (
	"embed"
	"encoding/json"
	"io/fs"
	"strings"

	rootembed "bm-tarkov-map-tracker"
)

const (
	SuffixDevA = "tarkov.dev_A"
	SuffixDevB = "tarkov.dev_B"
	SuffixCOM  = "eftarkov.com"
)

var (
	iconsFS  fs.FS
	mapsFS   fs.FS
	pointsFS fs.FS
)

func init() {
	if err := mountGameFS(rootembed.GameFS()); err != nil {
		panic(err)
	}
}

func mountGameFS(root embed.FS) error {
	var err error
	iconsFS, err = fs.Sub(root, "icons")
	if err != nil {
		return err
	}
	mapsFS, err = fs.Sub(root, "maps")
	if err != nil {
		return err
	}
	pointsFS, err = fs.Sub(root, "points")
	if err != nil {
		return err
	}
	loadCatalog()
	return nil
}

func loadCatalog() {
	var cat catalogFile
	data, err := fs.ReadFile(mapsFS, "catalog.json")
	if err != nil {
		catalogOrder = append([]string(nil), defaultCatalogOrder...)
		catalogDefault = "woods"
		return
	}
	if err := json.Unmarshal(data, &cat); err != nil || len(cat.Order) == 0 {
		catalogOrder = append([]string(nil), defaultCatalogOrder...)
		catalogDefault = "woods"
		return
	}
	catalogOrder = cat.Order
	catalogDefault = cat.Default
	if catalogDefault == "" {
		catalogDefault = "woods"
	}
}

type catalogFile struct {
	Order   []string `json:"order"`
	Default string   `json:"default"`
}

type mapPoints struct {
	PMC     json.RawMessage `json:"pmc"`
	Scav    json.RawMessage `json:"scav"`
	Coop    json.RawMessage `json:"coop"`
	Transit json.RawMessage `json:"transit"`
}

type mapBundle struct {
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
    EftarkovLevel       int       `json:"eftarkov_level,omitempty"`
	EftarkovCols        int       `json:"eftarkov_cols,omitempty"`
	EftarkovRows        int       `json:"eftarkov_rows,omitempty"`
	EftarkovTileSize    int       `json:"eftarkov_tile_size,omitempty"`
	Points              mapPoints `json:"points"`
}

type MapMeta struct {
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
    EftarkovLevel       int       `json:"eftarkov_level,omitempty"`
	EftarkovCols        int       `json:"eftarkov_cols,omitempty"`
	EftarkovRows        int       `json:"eftarkov_rows,omitempty"`
	EftarkovTileSize    int       `json:"eftarkov_tile_size,omitempty"`
}

var (
	catalogOrder   []string
	catalogDefault string
)

var defaultCatalogOrder = []string{
	"factory",
	"groundzero",
	"interchange",
	"lighthouse",
	"labs",
	"customs",
	"shoreline",
	"labyrinth",
	"reserve",
	"woods",
	"streets",
}

func CatalogOrder() []string {
	return append([]string(nil), catalogOrder...)
}

func CatalogDefault() string {
	return catalogDefault
}

func mapBaseName(mapID, suffix string) string {
	return mapID + "_" + suffix
}

func mapJSONPath(mapID, suffix string) string {
	return mapBaseName(mapID, suffix) + ".json"
}

func mapPNGPath(mapID, suffix string) string {
	return mapBaseName(mapID, suffix) + ".png"
}

func mapSVGPath(mapID, suffix string) string {
	return mapBaseName(mapID, suffix) + ".svg"
}

func mapOverlaySVGPath(mapID, suffix string) string {
	return mapBaseName(mapID, suffix) + ".overlay.svg"
}

func readMapBundle(mapID, suffix string) (mapBundle, error) {
	var bundle mapBundle
	data, err := fs.ReadFile(mapsFS, mapJSONPath(mapID, suffix))
	if err != nil {
		return bundle, err
	}
	if err := json.Unmarshal(data, &bundle); err != nil {
		return bundle, err
	}
	if bundle.Name == "" {
		bundle.Name = mapID
	}
	return bundle, nil
}

func bundleToMeta(b mapBundle) MapMeta {
	return MapMeta{
		Name:                b.Name,
		DisplayName:         b.DisplayName,
		Description:         b.Description,
		XMin:                b.XMin,
		XMax:                b.XMax,
		ZMin:                b.ZMin,
		ZMax:                b.ZMax,
		CoordinatesRotation: b.CoordinatesRotation,
		DisplayRotation:     b.DisplayRotation,
		Width:               b.Width,
		Height:              b.Height,
		StitchWidth:         b.StitchWidth,
		StitchHeight:        b.StitchHeight,
		MapOffsetX:          b.MapOffsetX,
		MapOffsetY:          b.MapOffsetY,
		TileZoom:            b.TileZoom,
		TileMinX:            b.TileMinX,
		TileMinY:            b.TileMinY,
		TileMaxX:            b.TileMaxX,
		TileMaxY:            b.TileMaxY,
		TileSize:            b.TileSize,
		Transform:           b.Transform,
		SvgXMin:             b.SvgXMin,
		SvgXMax:             b.SvgXMax,
		SvgZMin:             b.SvgZMin,
		SvgZMax:             b.SvgZMax,
		MapAssetRev:         b.MapAssetRev,
		OverlayLeft:         b.OverlayLeft,
		OverlayTop:          b.OverlayTop,
		OverlayWidth:        b.OverlayWidth,
		OverlayHeight:       b.OverlayHeight,
		OverlayOpacity:      b.OverlayOpacity,
		EftarkovLevel:       b.EftarkovLevel,
		EftarkovCols:        b.EftarkovCols,
		EftarkovRows:        b.EftarkovRows,
		EftarkovTileSize:    b.EftarkovTileSize,
	}
}

func LoadMapCatalog(suffix string) (order []string, metaByID map[string]MapMeta, boundsJSON []byte) {
	metaByID = map[string]MapMeta{}
	for _, id := range catalogOrder {
		if !MapExists(suffix, id) {
			continue
		}
		bundle, err := readMapBundle(id, suffix)
		if err != nil {
			continue
		}
		meta := bundleToMeta(bundle)
		if meta.Name == "" {
			meta.Name = id
		}
		metaByID[id] = meta
		order = append(order, id)
	}
	aggregate := make(map[string]MapMeta, len(metaByID))
	for id, meta := range metaByID {
		aggregate[id] = meta
	}
	boundsJSON, _ = json.Marshal(aggregate)
	return order, metaByID, boundsJSON
}

func MapPNG(suffix, mapID string) ([]byte, string, error) {
	data, err := fs.ReadFile(mapsFS, mapPNGPath(mapID, suffix))
	if err != nil || len(data) == 0 {
		return nil, "", fs.ErrNotExist
	}
	return data, "image/png", nil
}

func MapOverlaySVG(suffix, mapID string) ([]byte, error) {
	data, err := fs.ReadFile(mapsFS, mapOverlaySVGPath(mapID, suffix))
	if err != nil || len(data) == 0 {
		return nil, fs.ErrNotExist
	}
	return data, nil
}

func MapAsset(suffix, mapID string) ([]byte, string, error) {
	if suffix == SuffixDevA || suffix == SuffixDevB {
		if data, err := fs.ReadFile(mapsFS, mapSVGPath(mapID, suffix)); err == nil && len(data) > 0 {
			return data, "image/svg+xml", nil
		}
	}
	return MapPNG(suffix, mapID)
}

func MapExists(suffix, mapID string) bool {
	if suffix == SuffixDevA || suffix == SuffixDevB {
		if data, err := fs.ReadFile(mapsFS, mapSVGPath(mapID, suffix)); err == nil && len(data) > 0 {
			return true
		}
	}
	_, _, err := MapPNG(suffix, mapID)
	return err == nil
}

func TrayIconPNG() []byte {
	data, err := fs.ReadFile(iconsFS, "icon.png")
	if err != nil || len(data) == 0 {
		return nil
	}
	return data
}

func WindowIconICO() []byte {
	data, err := fs.ReadFile(iconsFS, "icon.ico")
	if err != nil || len(data) == 0 {
		return nil
	}
	return data
}

func PointIconPNG(name string) ([]byte, error) {
	name = strings.TrimSuffix(strings.TrimSpace(name), ".png")
	file := name + ".png"
	data, err := fs.ReadFile(pointsFS, file)
	if err != nil || len(data) == 0 {
		return nil, fs.ErrNotExist
	}
	return data, nil
}

func EftarkovPointsMetaJSON() ([]byte, error) {
	return fs.ReadFile(mapsFS, "eftarkov.meta.json")
}

var exfilKindField = map[string]func(mapPoints) json.RawMessage{
	"pmc":     func(p mapPoints) json.RawMessage { return p.PMC },
	"scav":    func(p mapPoints) json.RawMessage { return p.Scav },
	"coop":    func(p mapPoints) json.RawMessage { return p.Coop },
	"transit": func(p mapPoints) json.RawMessage { return p.Transit },
}

func AggregatedExfilJSON(suffix, kind string) ([]byte, error) {
	pick, ok := exfilKindField[kind]
	if !ok {
		return nil, fs.ErrNotExist
	}
	out := make(map[string]json.RawMessage)
	for _, id := range catalogOrder {
		if !MapExists(suffix, id) {
			continue
		}
		bundle, err := readMapBundle(id, suffix)
		if err != nil {
			continue
		}
		rows := pick(bundle.Points)
		if len(rows) == 0 || string(rows) == "null" {
			continue
		}
		out[id] = rows
	}
	if len(out) == 0 {
		return nil, fs.ErrNotExist
	}
	return json.Marshal(out)
}

func SanitizeMapID(suffix, id string, metaByID map[string]MapMeta, fallback string) string {
	id = strings.ToLower(strings.TrimSpace(id))
	id = strings.TrimSuffix(id, ".svg")
	id = strings.TrimSuffix(id, ".png")
	if id == "" {
		return fallback
	}
	if _, ok := metaByID[id]; ok {
		return id
	}
	if MapExists(suffix, id) {
		return id
	}
	return fallback
}
