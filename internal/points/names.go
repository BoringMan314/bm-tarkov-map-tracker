package points

import (
	"encoding/json"
	"io/fs"
	"strings"
	"sync"
)

var (
	namesOnce      sync.Once
	namesByID      map[string]map[string]string
	eftNamesOnce   sync.Once
	eftNamesByID   map[string]map[string]string
)

var localeToAPILang = map[string]string{
	"zh_TW": "zh_TW",
	"zh_CN": "zh_CN",
	"en_US": "en",
	"ja_JP": "ja",
	"cs_CZ": "cs",
	"fr_FR": "fr",
	"de_DE": "de",
	"hu_HU": "hu",
	"it_IT": "it",
	"ko_KR": "ko",
	"pl_PL": "pl",
	"pt_PT": "pt",
	"sk_SK": "sk",
	"es_ES": "es",
	"es_MX": "es",
	"tr_TR": "tr",
	"ru_RU": "ru",
	"ro_RO": "ro",
	"vi_VN": "en",
	"id_ID": "en",
	"th_TH": "en",
}

func loadNames() {
	namesOnce.Do(func() {
		namesByID = map[string]map[string]string{}
		data, err := fs.ReadFile(namesFS, "exfil/names.json")
		if err != nil || len(data) == 0 {
			return
		}
		_ = json.Unmarshal(data, &namesByID)
	})
}

func loadEftarkovNames() {
	eftNamesOnce.Do(func() {
		eftNamesByID = map[string]map[string]string{}
		data, err := fs.ReadFile(namesFS, "eftarkov/names.json")
		if err != nil || len(data) == 0 {
			return
		}
		_ = json.Unmarshal(data, &eftNamesByID)
	})
}

func ExfilName(id, locale, fallback string) string {
	loadNames()
	loadEftarkovNames()
	if id == "" {
		return fallback
	}
	langs, ok := namesByID[id]
	if !ok {
		langs, ok = eftNamesByID[id]
	}
	if !ok {
		return fallback
	}
	if apiLang, ok := localeToAPILang[locale]; ok {
		if name, ok := langs[apiLang]; ok && name != "" {
			return name
		}
		if apiLang == "zh_CN" {
			if name, ok := langs["zh"]; ok && name != "" {
				return name
			}
		}
	}
	if base, _, ok := strings.Cut(locale, "_"); ok && base != "" {
		if name, ok := langs[base]; ok && name != "" {
			return name
		}
	}
	if name, ok := langs["en"]; ok && name != "" {
		return name
	}
	return fallback
}

func ExfilNamesForLocale(locale string) map[string]string {
	loadNames()
	loadEftarkovNames()
	out := make(map[string]string, len(namesByID)+len(eftNamesByID))
	for id := range namesByID {
		fallback := ""
		if langs, ok := namesByID[id]; ok {
			fallback = langs["en"]
		}
		out[id] = ExfilName(id, locale, fallback)
	}
	for id := range eftNamesByID {
		if _, exists := out[id]; exists {
			continue
		}
		fallback := ""
		if langs, ok := eftNamesByID[id]; ok {
			fallback = langs["en"]
		}
		out[id] = ExfilName(id, locale, fallback)
	}
	return out
}

// AllExfilEnglishNames returns every known exfil/transit id with its English label.
func AllExfilEnglishNames() map[string]string {
	loadNames()
	loadEftarkovNames()
	out := make(map[string]string, len(namesByID)+len(eftNamesByID))
	for id, langs := range namesByID {
		if name := englishName(langs); name != "" {
			out[id] = name
		}
	}
	for id, langs := range eftNamesByID {
		if _, exists := out[id]; exists {
			continue
		}
		if name := englishName(langs); name != "" {
			out[id] = name
		}
	}
	return out
}

func englishName(langs map[string]string) string {
	if name, ok := langs["en"]; ok && name != "" {
		return name
	}
	return ""
}
