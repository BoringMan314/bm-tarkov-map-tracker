package localehttp

import (
	"encoding/json"
	"net/http"
	"strings"

	"bm-tarkov-map-tracker/internal/config"
	"bm-tarkov-map-tracker/internal/i18n"
)

type Payload struct {
	Locale      string            `json:"locale"`
	Order       []string          `json:"order"`
	Labels      map[string]string `json:"labels"`
	Strings     map[string]string `json:"strings"`
	MapNames    map[string]string `json:"mapNames"`
	ExfilNames  map[string]string `json:"exfilNames"`
	WindowTitle string            `json:"windowTitle"`
}

type setRequest struct {
	Locale string `json:"locale"`
}

var onChange func()

func SetOnChange(fn func()) {
	onChange = fn
}

func Register(mux *http.ServeMux) {
	mux.HandleFunc("/api/locale", handleLocale)
	mux.HandleFunc("/api/locale/set", handleSet)
}

func handleLocale(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	writePayload(w)
}

func handleSet(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req setRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	code := strings.TrimSpace(req.Locale)
	if code == "" {
		http.Error(w, "locale required", http.StatusBadRequest)
		return
	}
	if err := config.SetActiveLocale(code); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if onChange != nil {
		onChange()
	}
	writePayload(w)
}

func writePayload(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(Payload{
		Locale:      i18n.GetLocale(),
		Order:       i18n.LocaleOrder(),
		Labels:      i18n.LocaleLabels(),
		Strings:     i18n.UIStrings(),
		MapNames:    i18n.MapNames(),
		ExfilNames:  i18n.ExfilNames(),
		WindowTitle: i18n.WindowTitle(),
	})
}
