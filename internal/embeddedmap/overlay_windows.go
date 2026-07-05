//go:build windows

package embeddedmap

import (
	"unsafe"

	"github.com/wailsapp/wails/v3/pkg/application"
	"golang.org/x/sys/windows"

	"bm-tarkov-map-tracker/internal/gamewin"
)

var (
	user32Overlay                    = windows.NewLazySystemDLL("user32.dll")
	dwmapi                           = windows.NewLazySystemDLL("dwmapi.dll")
	procDwmExtendFrameIntoClientArea = dwmapi.NewProc("DwmExtendFrameIntoClientArea")
	procGetWindowLongPtrW            = user32Overlay.NewProc("GetWindowLongPtrW")
	procSetWindowLongPtrW            = user32Overlay.NewProc("SetWindowLongPtrW")
	procShowWindow                   = user32Overlay.NewProc("ShowWindow")
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

func ensureOverlayConfigured(win application.Window, configured *bool) {
	if win == nil || (configured != nil && *configured) {
		return
	}
	hwnd := uintptr(win.NativeWindow())
	if hwnd == 0 || !gamewin.IsWindowValid(hwnd) {
		return
	}

	style, _, _ := procGetWindowLongPtrW.Call(hwnd, gwlExStyle)
	procSetWindowLongPtrW.Call(hwnd, gwlExStyle, style|wsExNoActivate)

	m := margins{-1, -1, -1, -1}
	_, _, _ = procDwmExtendFrameIntoClientArea.Call(
		hwnd,
		uintptr(unsafe.Pointer(&m)),
	)
	win.SetBackgroundColour(application.NewRGBA(0, 0, 0, 0))
	if configured != nil {
		*configured = true
	}
}

func refreshOverlayTransparency(win application.Window) {
	if win == nil {
		return
	}
	hwnd := uintptr(win.NativeWindow())
	if hwnd == 0 || !gamewin.IsWindowValid(hwnd) {
		return
	}
	m := margins{-1, -1, -1, -1}
	_, _, _ = procDwmExtendFrameIntoClientArea.Call(
		hwnd,
		uintptr(unsafe.Pointer(&m)),
	)
	win.SetBackgroundColour(application.NewRGBA(0, 0, 0, 0))
}

func polishOverlayWindow(win application.Window) {
	var configured bool
	ensureOverlayConfigured(win, &configured)
}

func showOverlayNoActivate(win application.Window) bool {
	if win == nil {
		return false
	}
	hwnd := uintptr(win.NativeWindow())
	if hwnd == 0 || !gamewin.IsWindowValid(hwnd) {
		return false
	}
	procShowWindow.Call(hwnd, swShowNoActivate)
	refreshOverlayTransparency(win)
	return true
}

func hideOverlayWindow(win application.Window) {
	if win == nil {
		return
	}
	win.Hide()
	hwnd := uintptr(win.NativeWindow())
	if hwnd == 0 || !gamewin.IsWindowValid(hwnd) {
		return
	}
	procShowWindow.Call(hwnd, swHide)
}
