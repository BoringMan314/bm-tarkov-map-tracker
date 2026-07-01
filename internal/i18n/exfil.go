package i18n

import (
	"strings"
)

const exfilKeyPrefix = "exfil_"

func ExfilKey(id string) string {
	return exfilKeyPrefix + id
}

func ExfilName(id, fallback string) string {
	if id == "" {
		return fallback
	}
	key := ExfilKey(id)
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
	return fallback
}

func ExfilNames() map[string]string {
	mu.RLock()
	defer mu.RUnlock()
	table, ok := tables[locale]
	if !ok {
		table = builtin["en_US"]
	}
	out := make(map[string]string)
	for key, value := range table {
		if !strings.HasPrefix(key, exfilKeyPrefix) || value == "" {
			continue
		}
		out[strings.TrimPrefix(key, exfilKeyPrefix)] = value
	}
	if len(out) > 0 {
		return out
	}
	if table, ok := builtin["en_US"]; ok {
		out = make(map[string]string)
		for key, value := range table {
			if !strings.HasPrefix(key, exfilKeyPrefix) || value == "" {
				continue
			}
			out[strings.TrimPrefix(key, exfilKeyPrefix)] = value
		}
	}
	return out
}
