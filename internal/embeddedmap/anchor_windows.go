//go:build windows

package embeddedmap

import (
	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/gamewin"
	"bm-tarkov-map-tracker/internal/winutil"
)

func mainWindowHWND(win application.Window) uintptr {
	var hwnd uintptr
	if win != nil {
		if nw := win.NativeWindow(); nw != nil {
			hwnd = uintptr(nw)
		}
	}
	if hwnd == 0 {
		hwnd = winutil.FindWindowByTitle(winutil.TrackedTitle())
	}
	return hwnd
}

func screenAnchorFromMain(win application.Window) (gamewin.WindowInfo, bool) {
	rc, ok := gamewin.MonitorWorkAreaForWindow(mainWindowHWND(win))
	if !ok {
		return fallbackWorkAreaAnchor()
	}
	return gamewin.WindowInfo{Rect: rc}, true
}
