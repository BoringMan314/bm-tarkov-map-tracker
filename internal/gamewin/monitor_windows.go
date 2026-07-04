//go:build windows

package gamewin

import "unsafe"

const monitorDefaultToNearest = 2

var (
	procMonitorFromWindow = user32.NewProc("MonitorFromWindow")
	procGetMonitorInfoW     = user32.NewProc("GetMonitorInfoW")
)

type monitorInfo struct {
	Size     uint32
	Monitor  win32Rect
	WorkArea win32Rect
	Flags    uint32
}

func MonitorWorkAreaForWindow(hwnd uintptr) (Rect, bool) {
	if hwnd == 0 {
		return PrimaryWorkAreaRect()
	}
	monitor, _, _ := procMonitorFromWindow.Call(hwnd, uintptr(monitorDefaultToNearest))
	if monitor == 0 {
		return PrimaryWorkAreaRect()
	}
	var info monitorInfo
	info.Size = uint32(unsafe.Sizeof(info))
	ok, _, _ := procGetMonitorInfoW.Call(monitor, uintptr(unsafe.Pointer(&info)))
	if ok == 0 {
		return PrimaryWorkAreaRect()
	}
	rc := rectFromWin32(info.WorkArea)
	if rc.Width() <= 0 || rc.Height() <= 0 {
		return Rect{}, false
	}
	return rc, true
}
