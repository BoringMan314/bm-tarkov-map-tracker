//go:build !windows

package gamewin

func WindowInfoFromHWND(_ uintptr) (WindowInfo, bool) {
	return WindowInfo{}, false
}
