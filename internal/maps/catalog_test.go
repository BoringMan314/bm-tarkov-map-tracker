package maps

import "testing"

func TestCatalogMapAssets(t *testing.T) {
	for _, id := range devACatalog.Order {
		if !devAMapExists(id) {
			t.Fatalf("%s: missing map asset", id)
		}
		w, h, ok := mapDimensionsFor("tarkovdev", "A", id)
		if !ok || w <= 0 || h <= 0 {
			t.Fatalf("%s: could not resolve dimensions", id)
		}
		meta, ok := devACatalog.MetaByID[id]
		if !ok {
			t.Fatalf("%s: missing meta.json", id)
		}
		if meta.Width > 0 && meta.Height > 0 {
			if diff(w, meta.Width) > 0.02 || diff(h, meta.Height) > 0.02 {
				t.Fatalf("%s: meta dimensions mismatch file=%v×%v meta=%v×%v", id, w, h, meta.Width, meta.Height)
			}
		}
		if data, mime, err := devAMapAsset(id); err != nil || len(data) == 0 {
			t.Fatalf("%s: map asset: %v", id, err)
		} else if mime == "image/svg+xml" {
			pw, ph, ok := parseViewBoxFromSVG("tarkovdev", id)
			if ok && (diff(w, pw) > 0.01 || diff(h, ph) > 0.01) {
				t.Fatalf("%s: viewBox mismatch file=%v×%v known=%v×%v", id, pw, ph, w, h)
			}
		}
	}
}

func parseViewBoxFromSVG(source, mapID string) (width, height float64, ok bool) {
	b, err := mapSVG(source, "A", mapID)
	if err != nil || len(b) == 0 {
		return 0, 0, false
	}
	head := b
	if len(head) > 4096 {
		head = head[:4096]
	}
	m := viewBoxRe.FindSubmatch(head)
	if len(m) < 2 {
		return 0, 0, false
	}
	return parseViewBox(string(m[1]))
}
