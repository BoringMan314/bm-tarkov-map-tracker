//go:build windows

package gamewin

func WindowInfoFromHWND(hwnd uintptr) (WindowInfo, bool) {
	if !isWindowValid(hwnd) {
		return WindowInfo{}, false
	}
	rc, ok := windowClientScreenRect(hwnd)
	if !ok || rc.Width() <= 0 || rc.Height() <= 0 {
		rc, ok = windowOuterRect(hwnd)
	}
	if !ok || rc.Width() <= 0 || rc.Height() <= 0 {
		return WindowInfo{}, false
	}
	return WindowInfo{
		Rect:    rc,
		Title:   windowTitle(hwnd),
		Class:   windowClass(hwnd),
		Process: processBaseName(hwnd),
		Hwnd:    hwnd,
	}, true
}
