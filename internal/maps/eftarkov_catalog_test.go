package maps

import "testing"

func TestEftarkovCatalog(t *testing.T) {
	for _, id := range comCatalog.Order {
		if !comMapExists(id) {
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
	if len(entries) != len(comCatalog.Order) {
		t.Fatalf("catalog count=%d want %d", len(entries), len(comCatalog.Order))
	}
}
