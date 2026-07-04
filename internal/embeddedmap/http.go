package embeddedmap

import (
	"encoding/json"
	"net/http"
)

func RegisterHTTP(mux *http.ServeMux) {
	mux.HandleFunc("GET /api/embedded/state", serveState)
	mux.HandleFunc("GET /api/embedded/settings", serveSettings)
	mux.HandleFunc("POST /api/embedded/settings", handleSettings)
	mux.HandleFunc("POST /api/embedded/context", handleContext)
	mux.HandleFunc("POST /api/embedded/viewport", handleViewport)
}

func serveState(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, Default.State())
}

func serveSettings(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, Default.Settings())
}

func handleSettings(w http.ResponseWriter, r *http.Request) {
	var s Settings
	if err := json.NewDecoder(r.Body).Decode(&s); err != nil {
		http.Error(w, "bad json", http.StatusBadRequest)
		return
	}
	Default.ApplySettings(s)
	if PersistSettings != nil {
		_ = PersistSettings(Default.Settings())
	}
	writeJSON(w, Default.Settings())
}

func handleContext(w http.ResponseWriter, r *http.Request) {
	var ctx Context
	if err := json.NewDecoder(r.Body).Decode(&ctx); err != nil {
		http.Error(w, "bad json", http.StatusBadRequest)
		return
	}
	Default.ApplyContext(ctx)
	writeJSON(w, Default.Context())
}

func handleViewport(w http.ResponseWriter, r *http.Request) {
	var v Viewport
	if err := json.NewDecoder(r.Body).Decode(&v); err != nil {
		http.Error(w, "bad json", http.StatusBadRequest)
		return
	}
	Default.ApplyViewport(v)
	w.WriteHeader(http.StatusNoContent)
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	_ = json.NewEncoder(w).Encode(v)
}
