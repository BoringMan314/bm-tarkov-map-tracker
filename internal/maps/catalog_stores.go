package maps

import (
	"io/fs"

	"bm-tarkov-map-tracker/internal/assets"
)

type mapCatalog struct {
	suffix     string
	Order      []string
	MetaByID   map[string]assets.MapMeta
	BoundsBlob []byte
}

var (
	devACatalog mapCatalog
	devBCatalog mapCatalog
	comCatalog  mapCatalog
)

func init() {
	devACatalog = loadMapCatalog(assets.SuffixDevA)
	devBCatalog = loadMapCatalog(assets.SuffixDevB)
	comCatalog = loadMapCatalog(assets.SuffixCOM)
}

func loadMapCatalog(suffix string) mapCatalog {
	order, meta, bounds := assets.LoadMapCatalog(suffix)
	return mapCatalog{
		suffix:     suffix,
		Order:      order,
		MetaByID:   meta,
		BoundsBlob: bounds,
	}
}

func catalogFallback() string {
	if fb := assets.CatalogDefault(); fb != "" {
		return fb
	}
	return "woods"
}

func metaRecordFromAssets(m assets.MapMeta) metaRecord {
	return metaRecord{
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
		EftarkovCols:        m.EftarkovCols,
		EftarkovRows:        m.EftarkovRows,
		EftarkovTileSize:    m.EftarkovTileSize,
		MapOffsetX:          m.MapOffsetX,
		MapOffsetY:          m.MapOffsetY,
	}
}

func metaByIDFromCatalog(cat mapCatalog) map[string]metaRecord {
	out := make(map[string]metaRecord, len(cat.MetaByID))
	for id, m := range cat.MetaByID {
		out[id] = metaRecordFromAssets(m)
	}
	return out
}

func comMetaByIDFromCatalog(cat mapCatalog) map[string]metaRecord {
	out := make(map[string]metaRecord, len(cat.MetaByID))
	for id, m := range cat.MetaByID {
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

func devAMapAsset(mapID string) ([]byte, string, error) {
	return assets.MapAsset(assets.SuffixDevA, mapID)
}

func devAMapOverlay(mapID string) ([]byte, error) {
	return assets.MapOverlaySVG(assets.SuffixDevA, mapID)
}

func devAMapExists(mapID string) bool {
	return assets.MapExists(assets.SuffixDevA, mapID)
}

func devASanitizeMapID(id string) string {
	return assets.SanitizeMapID(assets.SuffixDevA, id, devACatalog.MetaByID, catalogFallback())
}

func devBMapAsset(mapID string) ([]byte, string, error) {
	return assets.MapAsset(assets.SuffixDevB, mapID)
}

func devBMapOverlay(mapID string) ([]byte, error) {
	_ = mapID
	return nil, fs.ErrNotExist
}

func devBMapExists(mapID string) bool {
	return assets.MapExists(assets.SuffixDevB, mapID)
}

func devBSanitizeMapID(id string) string {
	return assets.SanitizeMapID(assets.SuffixDevB, id, devBCatalog.MetaByID, catalogFallback())
}

func comMapAsset(mapID string) ([]byte, string, error) {
	return assets.MapPNG(assets.SuffixCOM, mapID)
}

func comMapExists(mapID string) bool {
	return assets.MapExists(assets.SuffixCOM, mapID)
}

func comSanitizeMapID(id string) string {
	return assets.SanitizeMapID(assets.SuffixCOM, id, comCatalog.MetaByID, catalogFallback())
}
