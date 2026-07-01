package maps

import (
	"io/fs"
	"net/http"
	"strings"

	eftarkov "bm-tarkov-map-tracker/internal/maps_eftarkov.com"
	tarkovdev "bm-tarkov-map-tracker/internal/maps_tarkov.dev"
	tarkovdevb "bm-tarkov-map-tracker/internal/maps_tarkov.dev_B"
)

func NormalizeSource(source string) string {
	switch strings.ToLower(strings.TrimSpace(source)) {
	case "eftarkov", "eftarkov.com", "api.eftarkov.com":
		return "eftarkov"
	case "tarkovdev", "tarkov.dev", "":
		return "tarkovdev"
	default:
		return "tarkovdev"
	}
}

func SourceFromRequest(r *http.Request) string {
	return NormalizeSource(r.URL.Query().Get("source"))
}

// NormalizeMapVariant maps query values to A (satellite, default) or B (abstract).
func NormalizeMapVariant(variant string) string {
	switch strings.ToLower(strings.TrimSpace(variant)) {
	case "b", "abstract", "abs":
		return "B"
	case "a", "satellite", "sat", "":
		return "A"
	default:
		return "A"
	}
}

func MapVariantFromRequest(r *http.Request) string {
	return NormalizeMapVariant(r.URL.Query().Get("variant"))
}

type mapRequest struct {
	source  string
	variant string
}

func mapRequestFromHTTP(r *http.Request) mapRequest {
	source := SourceFromRequest(r)
	variant := "A"
	if NormalizeSource(source) == "tarkovdev" {
		variant = MapVariantFromRequest(r)
	}
	return mapRequest{source: source, variant: variant}
}

type catalogProvider interface {
	catalogOrder() []string
	metaByID() map[string]metaRecord
	mapAsset(string) ([]byte, string, error)
	mapOverlay(string) ([]byte, error)
	mapExists(string) bool
	sanitizeMapID(string) string
}

type metaRecord struct {
	Name                string
	DisplayName         string
	Width               float64
	Height              float64
	XMin                float64
	XMax                float64
	ZMin                float64
	ZMax                float64
	CoordinatesRotation int
	DisplayRotation     int
	TileZoom            int
	TileMinX            int
	TileMinY            int
	TileMaxX            int
	TileMaxY            int
	TileSize            int
	Transform           []float64
	SvgXMin             float64
	SvgXMax             float64
	SvgZMin             float64
	SvgZMax             float64
	MapAssetRev         string
	EftarkovCols        int
	EftarkovRows        int
	EftarkovTileSize    int
	MapOffsetX          float64
	MapOffsetY          float64
}

type tarkovdevStore struct{}

func (tarkovdevStore) boundsJSON() []byte { return tarkovdev.BoundsBlob }

func (tarkovdevStore) catalogOrder() []string { return tarkovdev.CatalogOrder }

func (tarkovdevStore) metaByID() map[string]metaRecord {
	out := make(map[string]metaRecord, len(tarkovdev.MetaByID))
	for id, m := range tarkovdev.MetaByID {
		out[id] = metaRecord{
			Name:                m.Name,
			DisplayName:         m.DisplayName,
			Width:               m.Width,
			Height:              m.Height,
			XMin:                m.XMin,
			XMax:                m.XMax,
			ZMin:                m.ZMin,
			ZMax:                m.ZMax,
			CoordinatesRotation: m.CoordinatesRotation,
			DisplayRotation:     m.DisplayRotation,
			TileZoom:            m.TileZoom,
			TileMinX:            m.TileMinX,
			TileMinY:            m.TileMinY,
			TileMaxX:            m.TileMaxX,
			TileMaxY:            m.TileMaxY,
			TileSize:            m.TileSize,
			Transform:           m.Transform,
			SvgXMin:             m.SvgXMin,
			SvgXMax:             m.SvgXMax,
			SvgZMin:             m.SvgZMin,
			SvgZMax:             m.SvgZMax,
			MapAssetRev:         m.MapAssetRev,
		}
	}
	return out
}

func (tarkovdevStore) mapAsset(id string) ([]byte, string, error) {
	return tarkovdev.MapAsset(id)
}

func (tarkovdevStore) mapOverlay(id string) ([]byte, error) {
	return tarkovdev.MapOverlayAsset(id)
}

func (tarkovdevStore) mapExists(id string) bool { return tarkovdev.MapExists(id) }

func (tarkovdevStore) sanitizeMapID(id string) string { return tarkovdev.SanitizeMapID(id) }

type tarkovdevbStore struct{}

func (tarkovdevbStore) boundsJSON() []byte { return tarkovdevb.BoundsBlob }

func (tarkovdevbStore) catalogOrder() []string { return tarkovdevb.CatalogOrder }

func (tarkovdevbStore) metaByID() map[string]metaRecord {
	out := make(map[string]metaRecord, len(tarkovdevb.MetaByID))
	for id, m := range tarkovdevb.MetaByID {
		out[id] = metaRecord{
			Name:                m.Name,
			DisplayName:         m.DisplayName,
			Width:               m.Width,
			Height:              m.Height,
			XMin:                m.XMin,
			XMax:                m.XMax,
			ZMin:                m.ZMin,
			ZMax:                m.ZMax,
			CoordinatesRotation: m.CoordinatesRotation,
			DisplayRotation:     m.DisplayRotation,
			TileZoom:            m.TileZoom,
			TileMinX:            m.TileMinX,
			TileMinY:            m.TileMinY,
			TileMaxX:            m.TileMaxX,
			TileMaxY:            m.TileMaxY,
			TileSize:            m.TileSize,
			Transform:           m.Transform,
			SvgXMin:             m.SvgXMin,
			SvgXMax:             m.SvgXMax,
			SvgZMin:             m.SvgZMin,
			SvgZMax:             m.SvgZMax,
		}
	}
	return out
}

func (tarkovdevbStore) mapAsset(id string) ([]byte, string, error) { return tarkovdevb.MapAsset(id) }

func (tarkovdevbStore) mapOverlay(id string) ([]byte, error) { return tarkovdevb.MapOverlayAsset(id) }

func (tarkovdevbStore) mapExists(id string) bool { return tarkovdevb.MapExists(id) }

func (tarkovdevbStore) sanitizeMapID(id string) string { return tarkovdevb.SanitizeMapID(id) }

type eftarkovStore struct{}

func (eftarkovStore) boundsJSON() []byte { return eftarkov.BoundsBlob }

func (eftarkovStore) catalogOrder() []string { return eftarkov.CatalogOrder }

func (eftarkovStore) metaByID() map[string]metaRecord {
	out := make(map[string]metaRecord, len(eftarkov.MetaByID))
	for id, m := range eftarkov.MetaByID {
		out[id] = metaRecord{
			Name:                m.Name,
			DisplayName:         m.DisplayName,
			Width:               m.Width,
			Height:              m.Height,
			CoordinatesRotation: m.CoordinatesRotation,
			EftarkovCols:        m.EftarkovCols,
			EftarkovRows:        m.EftarkovRows,
			EftarkovTileSize:    m.EftarkovTileSize,
			MapOffsetX:          m.MapOffsetX,
			MapOffsetY:          m.MapOffsetY,
			MapAssetRev:         m.MapAssetRev,
		}
	}
	return out
}

func (eftarkovStore) mapAsset(id string) ([]byte, string, error) { return eftarkov.MapAsset(id) }

func (eftarkovStore) mapOverlay(id string) ([]byte, error) { return nil, fs.ErrNotExist }

func (eftarkovStore) mapExists(id string) bool { return eftarkov.MapExists(id) }

func (eftarkovStore) sanitizeMapID(id string) string { return eftarkov.SanitizeMapID(id) }

func storeFor(req mapRequest) catalogProvider {
	switch NormalizeSource(req.source) {
	case "eftarkov":
		return eftarkovStore{}
	case "tarkovdev":
		if NormalizeMapVariant(req.variant) == "B" {
			return tarkovdevbStore{}
		}
		return tarkovdevStore{}
	default:
		return tarkovdevStore{}
	}
}

func boundsFor(req mapRequest) []byte {
	switch NormalizeSource(req.source) {
	case "eftarkov":
		return eftarkov.BoundsBlob
	case "tarkovdev":
		if NormalizeMapVariant(req.variant) == "B" {
			return tarkovdevb.BoundsBlob
		}
		return tarkovdev.BoundsBlob
	default:
		return tarkovdev.BoundsBlob
	}
}
