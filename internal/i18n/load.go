package i18n

import (
	"encoding/json"
	"io/fs"
	"sort"
	"strings"

	rootembed "bm-tarkov-map-tracker"
)

var localesFS fs.FS

type localeMeta struct {
	Code         string `json:"code"`
	LanguageName string `json:"language_name"`
}

type catalogFile struct {
	Order        []string          `json:"order"`
	Default      string            `json:"default"`
	DisplayNames map[string]string `json:"display_names"`
	KeyCounts    map[string]int    `json:"key_counts"`
}

var catalogMeta catalogFile

func loadBuiltinFromEmbed() {
	localesFS = rootembed.I18nFS()

	loadCatalogMeta()
	discoverAndLoadLocales()
	if len(builtin) == 0 {
		panic("i18n: no locale tables loaded")
	}
}

func loadCatalogMeta() {
	data, err := fs.ReadFile(localesFS, "catalog.json")
	if err != nil {
		return
	}
	if err := json.Unmarshal(data, &catalogMeta); err != nil {
		return
	}
	if len(catalogMeta.Order) > 0 {
		localeOrder = append([]string(nil), catalogMeta.Order...)
	}
	if len(catalogMeta.DisplayNames) > 0 {
		for code, name := range catalogMeta.DisplayNames {
			if name != "" {
				localeDisplayNames[code] = name
			}
		}
	}
}

func discoverAndLoadLocales() {
	codes := discoverLocaleCodes()
	if len(localeOrder) == 0 {
		localeOrder = append([]string(nil), codes...)
	} else {
		seen := map[string]struct{}{}
		for _, code := range localeOrder {
			seen[code] = struct{}{}
		}
		for _, code := range codes {
			if _, ok := seen[code]; ok {
				continue
			}
			localeOrder = append(localeOrder, code)
			seen[code] = struct{}{}
		}
	}

	builtin = map[string]LocaleTable{}
	for _, code := range localeOrder {
		table, meta, err := readLocaleTable(code)
		if err != nil {
			continue
		}
		builtin[code] = table
		if meta.LanguageName != "" {
			localeDisplayNames[code] = meta.LanguageName
		} else if table["language_name"] != "" {
			localeDisplayNames[code] = table["language_name"]
		}
	}
}

func discoverLocaleCodes() []string {
	entries, err := fs.ReadDir(localesFS, ".")
	if err != nil {
		return nil
	}
	var codes []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if name == "catalog.json" || !strings.HasSuffix(name, ".json") {
			continue
		}
		codes = append(codes, strings.TrimSuffix(name, ".json"))
	}
	sort.Strings(codes)
	return codes
}

func readLocaleTable(code string) (LocaleTable, localeMeta, error) {
	var meta localeMeta
	table := LocaleTable{}

	data, err := fs.ReadFile(localesFS, code+".json")
	if err != nil {
		return nil, meta, err
	}

	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, meta, err
	}

	if metaRaw, ok := raw["_meta"]; ok {
		_ = json.Unmarshal(metaRaw, &meta)
		delete(raw, "_meta")
	}

	for key, valueRaw := range raw {
		var value string
		if err := json.Unmarshal(valueRaw, &value); err != nil {
			continue
		}
		if key == "language_name" {
			continue
		}
		table[key] = value
	}

	if meta.LanguageName != "" {
		table["language_name"] = meta.LanguageName
	} else if name, ok := table["language_name"]; ok && name != "" {
		meta.LanguageName = name
	} else {
		meta.LanguageName = LocaleDisplayName(code)
		table["language_name"] = meta.LanguageName
	}
	if meta.Code == "" {
		meta.Code = code
	}

	return table, meta, nil
}

func KeyCounts() map[string]int {
	out := make(map[string]int, len(catalogMeta.KeyCounts))
	for code, count := range catalogMeta.KeyCounts {
		out[code] = count
	}
	if len(out) > 0 {
		return out
	}
	for code, table := range builtin {
		out[code] = len(table)
	}
	return out
}

func DefaultLocale() string {
	if catalogMeta.Default != "" {
		return catalogMeta.Default
	}
	return "zh_TW"
}

func LocaleMeta(code string) (languageName string, ok bool) {
	table, exists := builtin[code]
	if !exists {
		return "", false
	}
	name := table["language_name"]
	return name, name != ""
}
