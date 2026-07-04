package apphttp

import (
	"io/fs"
	"net/http"

	"bm-tarkov-map-tracker/internal/embeddedmap"
	"bm-tarkov-map-tracker/internal/localehttp"
	"bm-tarkov-map-tracker/internal/maps"
	"bm-tarkov-map-tracker/internal/player"
	"bm-tarkov-map-tracker/internal/points"
)

func Handler(frontend fs.FS) http.Handler {
	mux := http.NewServeMux()
	localehttp.Register(mux)
	embeddedmap.RegisterHTTP(mux)
	points.RegisterHTTP(mux)
	player.RegisterHTTP(mux)
	maps.RegisterHTTP(mux)
	maps.RegisterRoutes(mux, frontend)
	return mux
}
