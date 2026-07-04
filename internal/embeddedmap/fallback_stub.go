//go:build !windows

package embeddedmap

import "bm-tarkov-map-tracker/internal/gamewin"

func fallbackWorkAreaAnchor() (gamewin.WindowInfo, bool) {
	return gamewin.WindowInfo{}, false
}
