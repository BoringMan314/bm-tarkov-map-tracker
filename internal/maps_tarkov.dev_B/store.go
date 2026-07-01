package tarkovdevb

import (
	"io/fs"

	"bm-tarkov-map-tracker/internal/assets"
)

const mapSuffix = assets.SuffixDevB

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
	_ = mapID
	return nil, fs.ErrNotExist
}

func MapAsset(mapID string) ([]byte, string, error) {
	return assets.MapAsset(mapSuffix, mapID)
}

func MapExists(mapID string) bool {
	return assets.MapExists(mapSuffix, mapID)
}

func SanitizeMapID(id string) string {
	fallback := assets.CatalogDefault()
	if fallback == "" {
		fallback = "woods"
	}
	return assets.SanitizeMapID(mapSuffix, id, MetaByID, fallback)
}
