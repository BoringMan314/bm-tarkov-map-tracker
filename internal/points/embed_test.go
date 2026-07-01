package points

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"bm-tarkov-map-tracker/internal/assets"
)

func TestEmbeddedEftarkovExfil(t *testing.T) {
	data, err := assets.AggregatedExfilJSON(assets.SuffixCOM, "pmc")
	if err != nil {
		t.Fatalf("aggregate: %v", err)
	}
	var byMap map[string][]any
	if err := json.Unmarshal(data, &byMap); err != nil {
		t.Fatalf("json: %v", err)
	}
	if len(byMap["factory"]) == 0 {
		t.Fatal("factory pmc empty")
	}

	mux := http.NewServeMux()
	RegisterHTTP(mux)
	req := httptest.NewRequest(http.MethodGet, "/api/points/exfil/pmc?source=eftarkov", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	var served map[string][]any
	if err := json.Unmarshal(rec.Body.Bytes(), &served); err != nil {
		t.Fatalf("serve json: %v", err)
	}
	if len(served["factory"]) == 0 {
		t.Fatal("served factory pmc empty")
	}
}
