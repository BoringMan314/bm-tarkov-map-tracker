//go:build windows

package embeddedmap

import (
	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/gamewin"
	"bm-tarkov-map-tracker/internal/winutil"
)

func appWindowInfo(win application.Window) (gamewin.WindowInfo, bool) {
	var hwnd uintptr
	if win != nil {
		if nw := win.NativeWindow(); nw != nil {
			hwnd = uintptr(nw)
		}
	}
	if hwnd == 0 {
		hwnd = winutil.FindWindowByTitle(winutil.TrackedTitle())
	}
	if hwnd == 0 {
		return gamewin.WindowInfo{}, false
	}
	return gamewin.WindowInfoFromHWND(hwnd)
}
