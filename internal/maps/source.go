package maps

import (
	"io/fs"
	"net/http"
	"strings"
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

func (tarkovdevStore) boundsJSON() []byte { return devACatalog.BoundsBlob }

func (tarkovdevStore) catalogOrder() []string { return devACatalog.Order }

func (tarkovdevStore) metaByID() map[string]metaRecord { return metaByIDFromCatalog(devACatalog) }

func (tarkovdevStore) mapAsset(id string) ([]byte, string, error) { return devAMapAsset(id) }

func (tarkovdevStore) mapOverlay(id string) ([]byte, error) { return devAMapOverlay(id) }

func (tarkovdevStore) mapExists(id string) bool { return devAMapExists(id) }

func (tarkovdevStore) sanitizeMapID(id string) string { return devASanitizeMapID(id) }

type tarkovdevbStore struct{}

func (tarkovdevbStore) boundsJSON() []byte { return devBCatalog.BoundsBlob }

func (tarkovdevbStore) catalogOrder() []string { return devBCatalog.Order }

func (tarkovdevbStore) metaByID() map[string]metaRecord { return metaByIDFromCatalog(devBCatalog) }

func (tarkovdevbStore) mapAsset(id string) ([]byte, string, error) { return devBMapAsset(id) }

func (tarkovdevbStore) mapOverlay(id string) ([]byte, error) { return devBMapOverlay(id) }

func (tarkovdevbStore) mapExists(id string) bool { return devBMapExists(id) }

func (tarkovdevbStore) sanitizeMapID(id string) string { return devBSanitizeMapID(id) }

type eftarkovStore struct{}

func (eftarkovStore) boundsJSON() []byte { return comCatalog.BoundsBlob }

func (eftarkovStore) catalogOrder() []string { return comCatalog.Order }

func (eftarkovStore) metaByID() map[string]metaRecord { return comMetaByIDFromCatalog(comCatalog) }

func (eftarkovStore) mapAsset(id string) ([]byte, string, error) { return comMapAsset(id) }

func (eftarkovStore) mapOverlay(id string) ([]byte, error) {
	_ = id
	return nil, fs.ErrNotExist
}

func (eftarkovStore) mapExists(id string) bool { return comMapExists(id) }

func (eftarkovStore) sanitizeMapID(id string) string { return comSanitizeMapID(id) }

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
		return comCatalog.BoundsBlob
	case "tarkovdev":
		if NormalizeMapVariant(req.variant) == "B" {
			return devBCatalog.BoundsBlob
		}
		return devACatalog.BoundsBlob
	default:
		return devACatalog.BoundsBlob
	}
}
