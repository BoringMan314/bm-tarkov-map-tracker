//go:build !windows

package embeddedmap

import (
	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/gamewin"
)

func appWindowInfo(_ application.Window) (gamewin.WindowInfo, bool) {
	return gamewin.WindowInfo{}, false
}
