//go:build !windows

package gamewin

func refreshWindowInfo(info WindowInfo) (WindowInfo, bool) {
	if info.Hwnd == 0 {
		return WindowInfo{}, false
	}
	return info, info.Rect.Width() > 0
}

func isWindowValid(_ uintptr) bool {
	return false
}
