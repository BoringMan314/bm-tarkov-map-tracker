//go:build !windows

package embeddedmap

import (
	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/gamewin"
)

func applyOverlayBounds(win application.Window, position string, sizeDIP, offsetXDIP, offsetYDIP int, anchor gamewin.WindowInfo, last *application.Rect) {
	if win == nil || anchor.Rect.Width() <= 0 {
		return
	}
	x, y := cornerPosition(position, sizeDIP, offsetXDIP, offsetYDIP, anchor.Rect)
	win.SetSize(sizeDIP, sizeDIP)
	win.SetMinSize(sizeDIP, sizeDIP)
	win.SetMaxSize(sizeDIP, sizeDIP)
	win.SetPosition(x, y)
	if last != nil {
		*last = application.Rect{X: x, Y: y, Width: sizeDIP, Height: sizeDIP}
	}
}

func cornerPosition(position string, size, offsetX, offsetY int, game gamewin.Rect) (int, int) {
	switch position {
	case "top-left":
		return game.Left + offsetX, game.Top + offsetY
	case "top-right":
		return game.Right - size - offsetX, game.Top + offsetY
	case "bottom-left":
		return game.Left + offsetX, game.Bottom - size - offsetY
	case "bottom-right":
		return game.Right - size - offsetX, game.Bottom - size - offsetY
	default:
		return game.Left + offsetX, game.Top + offsetY
	}
}
