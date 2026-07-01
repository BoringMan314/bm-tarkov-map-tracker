package player

import (
	"encoding/json"
	"net/http"
)

func RegisterHTTP(mux *http.ServeMux) {
	mux.HandleFunc("GET /api/player/self", serveSelf)
}

func serveSelf(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	_ = json.NewEncoder(w).Encode(Default.Self())
}
