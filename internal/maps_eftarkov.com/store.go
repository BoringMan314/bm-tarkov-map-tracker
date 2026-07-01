package eftarkov

import (
	"bm-tarkov-map-tracker/internal/assets"
)

const mapSuffix = assets.SuffixCOM

type Meta = assets.MapMeta

var (
	CatalogOrder []string
	MetaByID     map[string]Meta
	BoundsBlob   []byte
)

func init() {
	CatalogOrder, MetaByID, BoundsBlob = assets.LoadMapCatalog(mapSuffix)
}

func MapAsset(mapID string) ([]byte, string, error) {
	return assets.MapPNG(mapSuffix, mapID)
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
