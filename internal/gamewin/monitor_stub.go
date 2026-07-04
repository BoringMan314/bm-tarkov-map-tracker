//go:build !windows

package gamewin

func MonitorWorkAreaForWindow(_ uintptr) (Rect, bool) {
	return Rect{}, false
}
