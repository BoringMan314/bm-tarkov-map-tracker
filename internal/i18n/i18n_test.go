package i18n_test

import (
	"testing"

	"bm-tarkov-map-tracker/internal/i18n"
	"bm-tarkov-map-tracker/internal/points"
)

func TestAllLocalesHaveRequiredKeys(t *testing.T) {
	required := i18n.BuiltinTables()["zh_TW"]
	if len(required) == 0 {
		t.Fatal("empty zh_TW table")
	}
	for code, table := range i18n.BuiltinTables() {
		for key := range required {
			if v, ok := table[key]; !ok || v == "" {
				t.Fatalf("%s missing key %q", code, key)
			}
		}
	}
}

func TestLocaleMetaPresent(t *testing.T) {
	name, ok := i18n.LocaleMeta("zh_TW")
	if !ok || name != "繁體中文" {
		t.Fatalf("zh_TW meta=%q ok=%v", name, ok)
	}
	name, ok = i18n.LocaleMeta("zh_CN")
	if !ok || name != "简体中文" {
		t.Fatalf("zh_CN meta=%q ok=%v", name, ok)
	}
}

func TestExfilLocalizedZhTW(t *testing.T) {
	table := i18n.BuiltinTables()["zh_TW"]
	key := i18n.ExfilKey("a11f20d1f462bc4c8f39699e8a59fc0b58b71299")
	got := table[key]
	if got != "3號門" {
		t.Fatalf("zh_TW Gate 3: got %q want 3號門", got)
	}
}

func TestExfilLocalizedZhCN(t *testing.T) {
	table := i18n.BuiltinTables()["zh_CN"]
	key := i18n.ExfilKey("a11f20d1f462bc4c8f39699e8a59fc0b58b71299")
	got := table[key]
	if got != "3号门" {
		t.Fatalf("zh_CN Gate 3: got %q want 3号门", got)
	}
}

func TestExfilEnglishFallbackEnUS(t *testing.T) {
	english := points.AllExfilEnglishNames()
	table := i18n.BuiltinTables()["en_US"]
	for id, want := range english {
		key := i18n.ExfilKey(id)
		got, ok := table[key]
		if !ok || got == "" {
			t.Fatalf("en_US missing %s", key)
		}
		if got != want {
			t.Fatalf("%s: got %q want %q", key, got, want)
		}
	}
}

func TestKeyCounts(t *testing.T) {
	counts := i18n.KeyCounts()
	if len(counts) != 21 {
		t.Fatalf("expected 21 locales, got %d", len(counts))
	}
	for code, count := range counts {
		if count != 390 {
			t.Fatalf("%s: expected 390 keys, got %d", code, count)
		}
	}
}

func TestExfilNamesPayload(t *testing.T) {
	i18n.SetLocale("zh_TW")
	names := i18n.ExfilNames()
	if len(names) == 0 {
		t.Fatal("empty exfil names")
	}
	if got := names["a11f20d1f462bc4c8f39699e8a59fc0b58b71299"]; got != "3號門" {
		t.Fatalf("zh_TW exfil payload Gate 3: got %q", got)
	}
}
