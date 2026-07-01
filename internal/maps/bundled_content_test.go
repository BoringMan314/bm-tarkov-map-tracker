package maps

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestBundledWoodsIsRaster(t *testing.T) {
	data, mime, err := mapAsset("tarkovdev", "A", "woods")
	if err != nil {
		t.Fatal(err)
	}
	if mime != "image/png" {
		t.Fatalf("woods mime=%q want image/png", mime)
	}
	if len(data) < 1_000_000 {
		t.Fatalf("woods png too small: %d bytes", len(data))
	}
}

func TestLabsUsesRasterPNG(t *testing.T) {
	data, mime, err := mapAsset("tarkovdev", "A", "labs")
	if err != nil {
		t.Fatal(err)
	}
	if mime != "image/png" {
		t.Fatalf("labs mime=%q want image/png", mime)
	}
	if len(data) < 1_000_000 {
		t.Fatalf("labs png too small: %d bytes", len(data))
	}
	w, h, ok := mapDimensionsFor("tarkovdev", "A", "labs")
	if !ok || w <= 0 || h <= 0 {
		t.Fatalf("labs dimensions invalid: %v×%v ok=%v", w, h, ok)
	}
}

func TestServeBundledMapByID(t *testing.T) {
	mux := http.NewServeMux()
	RegisterHTTP(mux)

	cases := []string{"woods", "factory", "shoreline"}
	for _, id := range cases {
		t.Run(id, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/api/map/"+id, nil)
			rec := httptest.NewRecorder()
			mux.ServeHTTP(rec, req)
			if rec.Code != http.StatusOK {
				t.Fatalf("status=%d", rec.Code)
			}
			if got := rec.Header().Get("X-Map-Id"); got != id {
				t.Fatalf("X-Map-Id=%q want %q", got, id)
			}
		})
	}
}
