package tarkovdev

import (
	"io/fs"

	"bm-tarkov-map-tracker/internal/assets"
)

const mapSuffix = assets.SuffixDevA

type Meta = assets.MapMeta

var (
	CatalogOrder []string
	MetaByID     map[string]Meta
	BoundsBlob   []byte
)

func init() {
	CatalogOrder, MetaByID, BoundsBlob = assets.LoadMapCatalog(mapSuffix)
}

func MapOverlayAsset(mapID string) ([]byte, error) {
	return assets.MapOverlaySVG(mapSuffix, mapID)
}

func MapAsset(mapID string) ([]byte, string, error) {
	return assets.MapPNG(mapSuffix, mapID)
}

func MapExists(mapID string) bool {
	return assets.MapExists(mapSuffix, mapID)
}

func MapSVG(mapID string) ([]byte, error) {
	_, mime, err := MapAsset(mapID)
	if err != nil {
		return nil, err
	}
	if mime != "image/svg+xml" {
		return nil, fs.ErrNotExist
	}
	data, _, err := MapAsset(mapID)
	return data, err
}

func SanitizeMapID(id string) string {
	fallback := assets.CatalogDefault()
	if fallback == "" {
		fallback = "woods"
	}
	return assets.SanitizeMapID(mapSuffix, id, MetaByID, fallback)
}
