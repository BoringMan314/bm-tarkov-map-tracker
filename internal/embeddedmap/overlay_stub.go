//go:build !windows

package embeddedmap

import "github.com/wailsapp/wails/v3/pkg/application"

func ensureOverlayConfigured(win application.Window, configured *bool) {
	if win == nil || (configured != nil && *configured) {
		return
	}
	win.SetBackgroundColour(application.NewRGBA(0, 0, 0, 0))
	if configured != nil {
		*configured = true
	}
}

func polishOverlayWindow(application.Window) {}

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
