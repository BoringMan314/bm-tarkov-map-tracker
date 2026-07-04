package maps

import (
	"encoding/json"
	"net/http"

	"bm-tarkov-map-tracker/internal/i18n"
)

type CatalogItem struct {
	ID          string  `json:"id"`
	DisplayName string  `json:"displayName"`
	SVGURL      string  `json:"svgUrl"`
	Width       float64 `json:"width"`
	Height      float64 `json:"height"`
}

func RegisterHTTP(mux *http.ServeMux) {
	mux.HandleFunc("GET /api/maps", serveCatalog)
	mux.HandleFunc("GET /api/maps/bounds", ServeBounds)
	mux.HandleFunc("GET /api/map/{id}/overlay", serveMapOverlay)
	mux.HandleFunc("GET /api/map/{id}", serveMapAsset)
}

func serveCatalog(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	req := mapRequestFromHTTP(r)
	entries, err := ListFor(req.source, req.variant)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	out := make([]CatalogItem, 0, len(entries))
	for _, entry := range entries {
		display := i18n.MapName(entry.ID, entry.DisplayName)
		out = append(out, CatalogItem{
			ID:          entry.ID,
			DisplayName: display,
			SVGURL:      entry.SVGURL,
			Width:       entry.Width,
			Height:      entry.Height,
		})
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Map-Source", NormalizeSource(req.source))
	w.Header().Set("X-Map-Default", DefaultMapID())
	if NormalizeSource(req.source) == "tarkovdev" {
		w.Header().Set("X-Map-Variant", NormalizeMapVariant(req.variant))
	}
	_ = json.NewEncoder(w).Encode(out)
}

func ServeBounds(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	req := mapRequestFromHTTP(r)
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Map-Source", NormalizeSource(req.source))
	if NormalizeSource(req.source) == "tarkovdev" {
		w.Header().Set("X-Map-Variant", NormalizeMapVariant(req.variant))
	}
	_, _ = w.Write(boundsFor(req))
}
