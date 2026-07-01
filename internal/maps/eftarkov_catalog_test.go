package maps

import (
	"testing"

	eftarkov "bm-tarkov-map-tracker/internal/maps_eftarkov.com"
)

func TestEftarkovCatalog(t *testing.T) {
	for _, id := range eftarkov.CatalogOrder {
		if !eftarkov.MapExists(id) {
			t.Errorf("%s: missing embedded map.png", id)
		}
	}
	entries, err := ListFor("eftarkov", "A")
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) == 0 {
		t.Fatal("eftarkov catalog empty")
	}
	if len(entries) != len(eftarkov.CatalogOrder) {
		t.Fatalf("catalog count=%d want %d", len(entries), len(eftarkov.CatalogOrder))
	}
}
