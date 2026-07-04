//go:build windows

package embeddedmap

import (
	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/gamewin"
)

func applyOverlayBounds(win application.Window, position string, sizeDIP, offsetXDIP, offsetYDIP int, anchor gamewin.WindowInfo, last *application.Rect) {
	if win == nil || anchor.Rect.Width() <= 0 || anchor.Rect.Height() <= 0 {
		return
	}

	dpi := gamewin.WindowDPI(anchor)
	sizePhys := scaleDIP(sizeDIP, dpi)
	if sizePhys <= 0 {
		return
	}
	offsetXPhys := scaleDIP(offsetXDIP, dpi)
	offsetYPhys := scaleDIP(offsetYDIP, dpi)

	physX, physY := cornerPhysical(position, sizePhys, offsetXPhys, offsetYPhys, anchor.Rect)
	physX, physY = clampOverlayPosition(physX, physY, sizePhys, anchor.Rect)

	physical := application.Rect{
		X:      physX,
		Y:      physY,
		Width:  sizePhys,
		Height: sizePhys,
	}
	if last != nil && boundsEqual(*last, physical) {
		return
	}

	win.SetBounds(application.PhysicalToDipRect(physical))
	if last != nil {
		*last = physical
	}
}

func boundsEqual(a, b application.Rect) bool {
	return a.X == b.X && a.Y == b.Y && a.Width == b.Width && a.Height == b.Height
}

func cornerPhysical(position string, sizePhys, offsetXPhys, offsetYPhys int, game gamewin.Rect) (int, int) {
	switch position {
	case "top-left":
		return game.Left + offsetXPhys, game.Top + offsetYPhys
	case "top-right":
		return game.Right - sizePhys - offsetXPhys, game.Top + offsetYPhys
	case "bottom-left":
		return game.Left + offsetXPhys, game.Bottom - sizePhys - offsetYPhys
	case "bottom-right":
		return game.Right - sizePhys - offsetXPhys, game.Bottom - sizePhys - offsetYPhys
	default:
		return game.Left + offsetXPhys, game.Top + offsetYPhys
	}
}

func clampOverlayPosition(x, y, sizePhys int, game gamewin.Rect) (int, int) {
	minX := game.Left
	minY := game.Top
	maxX := game.Right - sizePhys
	maxY := game.Bottom - sizePhys
	if maxX < minX {
		maxX = minX
	}
	if maxY < minY {
		maxY = minY
	}
	return clampInt(x, minX, maxX), clampInt(y, minY, maxY)
}

func clampInt(v, min, max int) int {
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}

func scaleDIP(dip, dpi int) int {
	if dip <= 0 {
		return 0
	}
	if dpi <= 0 {
		dpi = 96
	}
	return (dip * dpi) / 96
}
