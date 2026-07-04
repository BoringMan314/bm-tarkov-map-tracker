//go:build windows

package winutil

import (
	"os"
	"sync"
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	user32                    = windows.NewLazySystemDLL("user32.dll")
	kernel32                  = windows.NewLazySystemDLL("kernel32.dll")
	procEnumWindows           = user32.NewProc("EnumWindows")
	procGetWindowThreadProcId = user32.NewProc("GetWindowThreadProcessId")
	procBringWindowToTop      = user32.NewProc("BringWindowToTop")
	procSetForegroundWindow   = user32.NewProc("SetForegroundWindow")
	procAttachThreadInput     = user32.NewProc("AttachThreadInput")
	procGetForegroundWindow   = user32.NewProc("GetForegroundWindow")
	procGetWindowThread       = user32.NewProc("GetWindowThreadProcessId")
	procGetCurrentThreadId    = kernel32.NewProc("GetCurrentThreadId")
	procShowWindow            = user32.NewProc("ShowWindow")
	procSetWindowPos          = user32.NewProc("SetWindowPos")
	procFindWindowW           = user32.NewProc("FindWindowW")

	swRestore = 9
	swShow    = 5
	swpNoSize = 0x0001
	swpShow   = 0x0040
	hwndTop   = 0
)

func ActivateByTitle(title string) {
	hwnd := findWindow(title)
	if hwnd == 0 {
		return
	}
	activateHWND(hwnd)
}

func PlaceByTitle(title string, x, y int) {
	hwnd := findWindow(title)
	if hwnd == 0 {
		return
	}
	_, _, _ = procSetWindowPos.Call(
		hwnd,
		uintptr(hwndTop),
		uintptr(x),
		uintptr(y),
		0,
		0,
		uintptr(swpNoSize|swpShow),
	)
}

func ActivateAndPlace(title string, x, y int) {
	hwnd := findWindow(title)
	if hwnd == 0 {
		return
	}
	_, _, _ = procShowWindow.Call(hwnd, uintptr(swRestore))
	_, _, _ = procShowWindow.Call(hwnd, uintptr(swShow))
	PlaceByTitle(title, x, y)
	activateHWND(hwnd)
}

func findWindow(title string) uintptr {
	if title == "" {
		return 0
	}
	titlePtr, err := syscall.UTF16PtrFromString(title)
	if err != nil {
		return 0
	}
	hwnd, _, _ := procFindWindowW.Call(0, uintptr(unsafe.Pointer(titlePtr)))
	if hwnd != 0 {
		return hwnd
	}
	ourPID := uint32(os.Getpid())
	procGetWindowText := user32.NewProc("GetWindowTextW")
	var found uintptr
	cb := syscall.NewCallback(func(hwnd uintptr, _ uintptr) uintptr {
		var pid uint32
		procGetWindowThreadProcId.Call(hwnd, uintptr(unsafe.Pointer(&pid)))
		if pid != ourPID {
			return 1
		}
		var buf [512]uint16
		procGetWindowText.Call(hwnd, uintptr(unsafe.Pointer(&buf[0])), 512)
		if windows.UTF16ToString(buf[:]) != title {
			return 1
		}
		found = hwnd
		return 0
	})
	_, _, _ = procEnumWindows.Call(cb, 0)
	return found
}

func activateHWND(hwnd uintptr) {
	if hwnd == 0 {
		return
	}
	fg, _, _ := procGetForegroundWindow.Call()
	var fgThread uint32
	if fg != 0 {
		procGetWindowThread.Call(fg, uintptr(unsafe.Pointer(&fgThread)))
	}
	curThread, _, _ := procGetCurrentThreadId.Call()
	var targetThread uint32
	procGetWindowThread.Call(hwnd, uintptr(unsafe.Pointer(&targetThread)))
	if fgThread != 0 && fgThread != uint32(curThread) {
		_, _, _ = procAttachThreadInput.Call(curThread, uintptr(fgThread), 1)
	}
	if targetThread != uint32(curThread) {
		_, _, _ = procAttachThreadInput.Call(curThread, uintptr(targetThread), 1)
	}
	_, _, _ = procSetForegroundWindow.Call(hwnd)
	_, _, _ = procBringWindowToTop.Call(hwnd)
	if targetThread != uint32(curThread) {
		_, _, _ = procAttachThreadInput.Call(curThread, uintptr(targetThread), 0)
	}
	if fgThread != 0 && fgThread != uint32(curThread) {
		_, _, _ = procAttachThreadInput.Call(curThread, uintptr(fgThread), 0)
	}
}

var titleMu sync.RWMutex
var trackedTitle string

func SetTrackedTitle(title string) {
	titleMu.Lock()
	trackedTitle = title
	titleMu.Unlock()
}

func TrackedTitle() string {
	titleMu.RLock()
	defer titleMu.RUnlock()
	return trackedTitle
}

func ActivateTracked(x, y int) {
	ActivateAndPlace(TrackedTitle(), x, y)
}

func FindWindowByTitle(title string) uintptr {
	return findWindow(title)
}
