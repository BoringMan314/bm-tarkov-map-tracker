package i18n

import (
	"sync"

	"bm-tarkov-map-tracker/internal/appmeta"
)

type LocaleTable map[string]string

var (
	mu                 sync.RWMutex
	locale             string
	tables             map[string]LocaleTable
	builtin            map[string]LocaleTable
	localeOrder        []string
	localeDisplayNames = map[string]string{}
)

func init() {
	loadBuiltinFromEmbed()
	tables = cloneTables(builtin)
	locale = DefaultLocale()
}

func BuiltinTables() map[string]LocaleTable {
	return cloneTables(builtin)
}

func RequiredKeys() []string {
	keys := make([]string, 0, len(builtin["zh_TW"]))
	for k := range builtin["zh_TW"] {
		keys = append(keys, k)
	}
	return keys
}

func SetTables(next map[string]LocaleTable, active string) {
	mu.Lock()
	defer mu.Unlock()
	tables = cloneTables(next)
	locale = active
}

func SetLocale(code string) {
	mu.Lock()
	defer mu.Unlock()
	if _, ok := tables[code]; ok {
		locale = code
	}
}

func GetLocale() string {
	mu.RLock()
	defer mu.RUnlock()
	return locale
}

func T(key string) string {
	mu.RLock()
	defer mu.RUnlock()
	if table, ok := tables[locale]; ok {
		if v, ok := table[key]; ok {
			return v
		}
	}
	if table, ok := builtin["zh_TW"]; ok {
		if v, ok := table[key]; ok {
			return v
		}
	}
	return key
}

func ProjectName() string {
	return T("project_name")
}

func WindowTitle() string {
	return appmeta.WindowTitle(ProjectName())
}

func CycleLocales() []string {
	return LocaleOrder()
}

func LocaleOrder() []string {
	out := make([]string, len(localeOrder))
	copy(out, localeOrder)
	return out
}

func LocaleDisplayName(code string) string {
	if name, ok := localeDisplayNames[code]; ok {
		return name
	}
	return code
}

func LocaleLabels() map[string]string {
	out := make(map[string]string, len(localeOrder))
	for _, code := range localeOrder {
		out[code] = LocaleDisplayName(code)
	}
	return out
}

func UIStrings() map[string]string {
	keys := baseUIKeys()
	out := make(map[string]string, len(keys)+len(mapNameIDs()))
	for _, key := range keys {
		out[key] = T(key)
	}
	for _, id := range mapNameIDs() {
		out["map_"+id] = T("map_" + id)
	}
	return out
}

func baseUIKeys() []string {
	return []string{
		"language_name",
		"project_name",
		"map_tracker_label",
		"select_map",
		"map_error",
		"map_load_error",
		"reset_view",
		"marker_exfil_pmc",
		"marker_exfil_scav",
		"marker_exfil_transit",
		"marker_exfil_coop",
		"marker_exfil_group",
		"marker_exfil_show_names",
		"marker_player_position",
		"marker_player_center_lock",
		"point_source_label",
		"point_source_tarkovdev_a",
		"point_source_tarkovdev_b",
		"point_source_eftarkov",
		"settings",
		"about",
		"exit",
		"tray_restore",
		"download_update",
		"update_available_title",
	}
}

func MapName(id, fallback string) string {
	key := "map_" + id
	mu.RLock()
	defer mu.RUnlock()
	if table, ok := tables[locale]; ok {
		if v, ok := table[key]; ok && v != "" {
			return v
		}
	}
	if table, ok := builtin["en_US"]; ok {
		if v, ok := table[key]; ok && v != "" {
			return v
		}
	}
	if fallback != "" {
		return fallback
	}
	return id
}

func MapNames() map[string]string {
	out := make(map[string]string, len(mapNameIDs()))
	for _, id := range mapNameIDs() {
		out[id] = T("map_" + id)
	}
	return out
}

func mapNameIDs() []string {
	return []string{
		"factory",
		"groundzero",
		"interchange",
		"labs",
		"customs",
		"shoreline",
		"labyrinth",
		"reserve",
		"woods",
		"streets",
	}
}

func cloneTables(src map[string]LocaleTable) map[string]LocaleTable {
	out := make(map[string]LocaleTable, len(src))
	for code, table := range src {
		copyTable := make(LocaleTable, len(table))
		for k, v := range table {
			copyTable[k] = v
		}
		out[code] = copyTable
	}
	return out
}
