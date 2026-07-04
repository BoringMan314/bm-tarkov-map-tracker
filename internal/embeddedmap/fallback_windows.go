//go:build windows

package embeddedmap

import "bm-tarkov-map-tracker/internal/gamewin"

func fallbackWorkAreaAnchor() (gamewin.WindowInfo, bool) {
	rc, ok := gamewin.PrimaryWorkAreaRect()
	if !ok {
		return gamewin.WindowInfo{}, false
	}
	return gamewin.WindowInfo{Rect: rc}, true
}
