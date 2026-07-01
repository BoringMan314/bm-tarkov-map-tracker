package points

import (
	"net/http"
	"path"
	"strings"

	"bm-tarkov-map-tracker/internal/assets"
)

var exfilKinds = map[string]struct{}{
	"pmc":     {},
	"scav":    {},
	"transit": {},
	"coop":    {},
}

var iconNames = map[string]struct{}{
	"exfil-pmc":     {},
	"exfil-scav":    {},
	"exfil-transit": {},
	"exfil-coop":    {},
	"player":        {},
}

func RegisterHTTP(mux *http.ServeMux) {
	mux.HandleFunc("GET /api/points/exfil/{kind}", serveExfilJSON)
	mux.HandleFunc("GET /api/points/eftarkov/meta", serveEftarkovMeta)
	mux.HandleFunc("GET /api/points/icons/{name}", serveIconPNG)
}

func serveExfilJSON(w http.ResponseWriter, r *http.Request) {
	kind := strings.TrimSpace(r.PathValue("kind"))
	if kind == "" {
		kind = strings.TrimPrefix(r.URL.Path, "/api/points/exfil/")
		kind = strings.TrimSuffix(kind, ".json")
		if i := strings.IndexByte(kind, '?'); i >= 0 {
			kind = kind[:i]
		}
	}
	if _, ok := exfilKinds[kind]; !ok {
		http.NotFound(w, r)
		return
	}
	suffix := assets.SuffixDevA
	if normalizePointSource(r.URL.Query().Get("source")) == "eftarkov" {
		suffix = assets.SuffixCOM
	}
	data, err := assets.AggregatedExfilJSON(suffix, kind)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	_, _ = w.Write(data)
}

func serveEftarkovMeta(w http.ResponseWriter, r *http.Request) {
	data, err := assets.EftarkovPointsMetaJSON()
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	_, _ = w.Write(data)
}

func normalizePointSource(source string) string {
	switch strings.ToLower(strings.TrimSpace(source)) {
	case "eftarkov", "eftarkov.com", "api.eftarkov.com":
		return "eftarkov"
	case "tarkovdev", "tarkov.dev", "":
		return "tarkovdev"
	default:
		return "tarkovdev"
	}
}

func serveIconPNG(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimPrefix(r.URL.Path, "/api/points/icons/")
	name = strings.TrimSuffix(name, ".png")
	name = path.Base(name)
	if _, ok := iconNames[name]; !ok {
		http.NotFound(w, r)
		return
	}
	data, err := assets.PointIconPNG(name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "image/png")
	w.Header().Set("Cache-Control", "public, max-age=86400")
	_, _ = w.Write(data)
}
