package maps

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestServeCatalogEftarkov(t *testing.T) {
	mux := http.NewServeMux()
	RegisterHTTP(mux)

	req := httptest.NewRequest(http.MethodGet, "/api/maps?source=eftarkov", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	var items []CatalogItem
	if err := json.Unmarshal(rec.Body.Bytes(), &items); err != nil {
		t.Fatalf("json: %v body=%q", err, rec.Body.String()[:min(200, len(rec.Body.String()))])
	}
	if len(items) == 0 {
		t.Fatal("empty eftarkov catalog")
	}
	t.Logf("eftarkov catalog: %d maps, first=%s", len(items), items[0].ID)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
