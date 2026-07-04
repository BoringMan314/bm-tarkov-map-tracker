//go:build !windows

package embeddedmap

import "github.com/wailsapp/wails/v3/pkg/application"

func polishOverlayWindow(application.Window) {}

func configureOverlayWindow(win application.Window) {
	if win == nil {
		return
	}
	win.SetBackgroundColour(application.NewRGBA(0, 0, 0, 0))
}

func showOverlayNoActivate(win application.Window) bool {
	if win == nil {
		return false
	}
	win.Show()
	return true
}

func hideOverlayWindow(win application.Window) {
	if win != nil {
		win.Hide()
	}
}
