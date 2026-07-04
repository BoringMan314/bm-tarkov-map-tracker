//go:build !windows

package embeddedmap

import (
	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/gamewin"
)

func screenAnchorFromMain(_ application.Window) (gamewin.WindowInfo, bool) {
	return fallbackWorkAreaAnchor()
}
