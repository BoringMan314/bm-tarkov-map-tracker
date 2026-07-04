//go:build windows

package embeddedmap

import (
	"unsafe"

	"github.com/wailsapp/wails/v3/pkg/application"
	"golang.org/x/sys/windows"
)

var (
	dwmapi                           = windows.NewLazySystemDLL("dwmapi.dll")
	procDwmExtendFrameIntoClientArea = dwmapi.NewProc("DwmExtendFrameIntoClientArea")
	procGetWindowLongPtrW            = user32.NewProc("GetWindowLongPtrW")
	procSetWindowLongPtrW            = user32.NewProc("SetWindowLongPtrW")
	procShowWindow                   = user32.NewProc("ShowWindow")
)

const (
	gwlExStyle       = ^uintptr(19)
	wsExNoActivate   = 0x08000000
	swShowNoActivate = 4
	swHide           = 0
)

type margins struct {
	left, right, top, bottom int32
}

func configureOverlayWindow(win application.Window) {
	if win == nil {
		return
	}
	hwnd := uintptr(win.NativeWindow())
	if hwnd == 0 {
		return
	}
	style, _, _ := procGetWindowLongPtrW.Call(hwnd, gwlExStyle)
	procSetWindowLongPtrW.Call(hwnd, gwlExStyle, style|wsExNoActivate)

	m := margins{0, 0, 0, 0}
	_, _, _ = procDwmExtendFrameIntoClientArea.Call(
		hwnd,
		uintptr(unsafe.Pointer(&m)),
	)
	win.SetBackgroundColour(application.NewRGBA(0, 0, 0, 0))
}

func polishOverlayWindow(win application.Window) {
	configureOverlayWindow(win)
}

func showOverlayNoActivate(win application.Window) bool {
	if win == nil {
		return false
	}
	hwnd := uintptr(win.NativeWindow())
	if hwnd == 0 {
		return false
	}
	configureOverlayWindow(win)
	procShowWindow.Call(hwnd, swShowNoActivate)
	return true
}

func hideOverlayWindow(win application.Window) {
	if win == nil {
		return
	}
	hwnd := uintptr(win.NativeWindow())
	if hwnd == 0 {
		win.Hide()
		return
	}
	procShowWindow.Call(hwnd, swHide)
}
