package maps

import (
	"strings"
	"testing"

	"bm-tarkov-map-tracker/internal/assets"
)

func TestLighthouseInCatalog(t *testing.T) {
	order := devACatalog.Order
	if !containsID(order, "lighthouse") {
		t.Fatalf("dev A order missing lighthouse: %v", order)
	}
	list, err := ListFor("tarkovdev", "A")
	if err != nil {
		t.Fatal(err)
	}
	if !containsEntry(list, "lighthouse") {
		ids := make([]string, len(list))
		for i, e := range list {
			ids[i] = e.ID
		}
		t.Fatalf("ListFor dev A missing lighthouse; ids=%v", ids)
	}
	if !assets.MapExists(assets.SuffixDevA, "lighthouse") {
		t.Fatal("MapExists dev A lighthouse=false")
	}
}

func containsID(order []string, id string) bool {
	for _, x := range order {
		if x == id {
			return true
		}
	}
	return false
}

func containsEntry(list []Entry, id string) bool {
	for _, e := range list {
		if e.ID == id {
			return true
		}
	}
	return false
}

func TestLighthouseCatalogOrder(t *testing.T) {
	order := devACatalog.Order
	idxLh := indexOf(order, "lighthouse")
	idxIc := indexOf(order, "interchange")
	idxLb := indexOf(order, "labs")
	if idxLh < 0 {
		t.Fatal("lighthouse not in order")
	}
	if idxIc < 0 || idxLb < 0 || !(idxIc < idxLh && idxLh < idxLb) {
		t.Fatalf("order around lighthouse wrong: interchange@%d lighthouse@%d labs@%d", idxIc, idxLh, idxLb)
	}
}

func indexOf(ss []string, s string) int {
	for i, x := range ss {
		if x == s {
			return i
		}
	}
	return -1
}

func TestLighthouseDevAAsset(t *testing.T) {
	data, mime, err := devAMapAsset("lighthouse")
	if err != nil {
		t.Fatal(err)
	}
	if len(data) == 0 {
		t.Fatal("empty lighthouse asset")
	}
	if mime != "image/png" && mime != "image/svg+xml" {
		t.Fatalf("unexpected mime %q", mime)
	}
	if !strings.HasPrefix(mime, "image/") {
		t.Fatalf("bad mime %q", mime)
	}
}
