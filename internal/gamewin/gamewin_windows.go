//go:build windows

package gamewin

import (
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	user32                       = windows.NewLazySystemDLL("user32.dll")
	kernel32                     = windows.NewLazySystemDLL("kernel32.dll")
	procEnumWindows              = user32.NewProc("EnumWindows")
	procGetWindowRect            = user32.NewProc("GetWindowRect")
	procGetClientRect            = user32.NewProc("GetClientRect")
	procClientToScreen           = user32.NewProc("ClientToScreen")
	procIsIconic                 = user32.NewProc("IsIconic")
	procIsWindowVisible          = user32.NewProc("IsWindowVisible")
	procGetWindowTextW           = user32.NewProc("GetWindowTextW")
	procGetClassNameW            = user32.NewProc("GetClassNameW")
	procGetWindowThreadProcessId = user32.NewProc("GetWindowThreadProcessId")
	procGetDpiForWindow          = user32.NewProc("GetDpiForWindow")
	procIsWindow                 = user32.NewProc("IsWindow")
	procSystemParametersInfoW    = user32.NewProc("SystemParametersInfoW")
)

const spiGetWorkArea = 0x0030

type win32Rect struct {
	Left   int32
	Top    int32
	Right  int32
	Bottom int32
}

type point struct {
	X int32
	Y int32
}

func rectFromWin32(rc win32Rect) Rect {
	return Rect{
		Left:   int(rc.Left),
		Top:    int(rc.Top),
		Right:  int(rc.Right),
		Bottom: int(rc.Bottom),
	}
}

func FindEFTWindow() (WindowInfo, bool) {
	if info, ok := findEFTWindowByProcess(); ok {
		return info, true
	}
	return findEFTWindowByEnum()
}

func PrimaryWorkAreaRect() (Rect, bool) {
	var rc win32Rect
	ok, _, _ := procSystemParametersInfoW.Call(
		uintptr(spiGetWorkArea),
		0,
		uintptr(unsafe.Pointer(&rc)),
		0,
	)
	out := rectFromWin32(rc)
	if ok == 0 || out.Width() <= 0 || out.Height() <= 0 {
		return Rect{}, false
	}
	return out, true
}

func findEFTWindowByProcess() (WindowInfo, bool) {
	pids, err := eftProcessIDs()
	if err != nil || len(pids) == 0 {
		return WindowInfo{}, false
	}
	var best WindowInfo
	var bestArea int
	for _, pid := range pids {
		if info, ok := largestWindowForProcess(pid); ok {
			area := info.Rect.Width() * info.Rect.Height()
			if area > bestArea {
				bestArea = area
				best = info
			}
		}
	}
	return best, bestArea > 0
}

func findEFTWindowByEnum() (WindowInfo, bool) {
	var best WindowInfo
	var bestArea int
	var found bool
	cb := syscall.NewCallback(func(hwnd uintptr, _ uintptr) uintptr {
		if !isCandidateGameWindow(hwnd) {
			return 1
		}
		info, ok := windowInfoFromHWND(hwnd)
		if !ok {
			return 1
		}
		area := info.Rect.Width() * info.Rect.Height()
		if area < 640*480 {
			return 1
		}
		if area <= bestArea {
			return 1
		}
		bestArea = area
		best = info
		found = true
		return 1
	})
	_, _, _ = procEnumWindows.Call(cb, 0)
	return best, found
}

func largestWindowForProcess(pid uint32) (WindowInfo, bool) {
	var best WindowInfo
	var bestArea int
	var found bool
	cb := syscall.NewCallback(func(hwnd uintptr, _ uintptr) uintptr {
		var wpid uint32
		procGetWindowThreadProcessId.Call(hwnd, uintptr(unsafe.Pointer(&wpid)))
		if wpid != pid {
			return 1
		}
		iconic, _, _ := procIsIconic.Call(hwnd)
		if iconic != 0 {
			return 1
		}
		info, ok := windowInfoFromHWND(hwnd)
		if !ok {
			return 1
		}
		area := info.Rect.Width() * info.Rect.Height()
		if area < 640*480 {
			return 1
		}
		if area <= bestArea {
			return 1
		}
		bestArea = area
		best = info
		found = true
		return 1
	})
	_, _, _ = procEnumWindows.Call(cb, 0)
	return best, found
}

func eftProcessIDs() ([]uint32, error) {
	snapshot, err := windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPPROCESS, 0)
	if err != nil {
		return nil, err
	}
	defer windows.CloseHandle(snapshot)

	var entry windows.ProcessEntry32
	entry.Size = uint32(unsafe.Sizeof(entry))
	if err := windows.Process32First(snapshot, &entry); err != nil {
		return nil, err
	}
	var pids []uint32
	for {
		name := strings.ToLower(windows.UTF16ToString(entry.ExeFile[:]))
		if isEFTProcessName(name) {
			pids = append(pids, entry.ProcessID)
		}
		if err := windows.Process32Next(snapshot, &entry); err != nil {
			break
		}
	}
	return pids, nil
}

func isEFTProcessName(name string) bool {
	return name == "escapefromtarkov.exe"
}

func WindowDPI(info WindowInfo) int {
	return windowDPI(info.Hwnd)
}

func refreshWindowInfo(info WindowInfo) (WindowInfo, bool) {
	if !isWindowValid(info.Hwnd) {
		return WindowInfo{}, false
	}
	updated, ok := windowInfoFromHWND(info.Hwnd)
	if !ok {
		return WindowInfo{}, false
	}
	info.Rect = updated.Rect
	info.Title = updated.Title
	info.Class = updated.Class
	info.Process = updated.Process
	return info, true
}

func windowInfoFromHWND(hwnd uintptr) (WindowInfo, bool) {
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

func isWindowValid(hwnd uintptr) bool {
	if hwnd == 0 {
		return false
	}
	ok, _, _ := procIsWindow.Call(hwnd)
	return ok != 0
}

func isCandidateGameWindow(hwnd uintptr) bool {
	if hwnd == 0 {
		return false
	}
	iconic, _, _ := procIsIconic.Call(hwnd)
	if iconic != 0 {
		return false
	}

	path := processImagePath(hwnd)
	base := strings.ToLower(filepath.Base(path))
	if isEFTProcessPath(base, path) {
		return true
	}

	title := windowTitle(hwnd)
	if isEFTTitle(title) {
		return isWindowUsable(hwnd)
	}

	class := windowClass(hwnd)
	if class != "UnityWndClass" {
		return false
	}
	if isEFTProcessPath(base, path) || strings.Contains(strings.ToLower(base), "tarkov") {
		return isWindowUsable(hwnd)
	}
	return isEFTTitle(title) && isWindowUsable(hwnd)
}

func isWindowUsable(hwnd uintptr) bool {
	visible, _, _ := procIsWindowVisible.Call(hwnd)
	if visible != 0 {
		return true
	}
	rc, ok := windowOuterRect(hwnd)
	return ok && rc.Width() >= 640 && rc.Height() >= 480
}

func windowTitle(hwnd uintptr) string {
	var title [512]uint16
	procGetWindowTextW.Call(hwnd, uintptr(unsafe.Pointer(&title[0])), uintptr(len(title)))
	return windows.UTF16ToString(title[:])
}

func windowClass(hwnd uintptr) string {
	var class [256]uint16
	procGetClassNameW.Call(hwnd, uintptr(unsafe.Pointer(&class[0])), uintptr(len(class)))
	return windows.UTF16ToString(class[:])
}

func processBaseName(hwnd uintptr) string {
	path := processImagePath(hwnd)
	if path == "" {
		return ""
	}
	return filepath.Base(path)
}

func processImagePath(hwnd uintptr) string {
	var pid uint32
	procGetWindowThreadProcessId.Call(hwnd, uintptr(unsafe.Pointer(&pid)))
	if pid == 0 {
		return ""
	}
	handle, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, pid)
	if err != nil {
		return ""
	}
	defer windows.CloseHandle(handle)
	var buf [windows.MAX_PATH]uint16
	size := uint32(len(buf))
	err = windows.QueryFullProcessImageName(handle, 0, &buf[0], &size)
	if err != nil {
		return ""
	}
	return windows.UTF16ToString(buf[:size])
}

func isEFTProcessPath(baseName, fullPath string) bool {
	if strings.EqualFold(baseName, "EscapeFromTarkov.exe") {
		return true
	}
	lower := strings.ToLower(fullPath)
	return strings.Contains(lower, `\escape from tarkov\`) &&
		strings.HasSuffix(lower, `\escapefromtarkov.exe`)
}

func windowDPI(hwnd uintptr) int {
	if hwnd == 0 {
		return 96
	}
	dpi, _, _ := procGetDpiForWindow.Call(hwnd)
	if dpi == 0 {
		return 96
	}
	return int(dpi)
}

func windowOuterRect(hwnd uintptr) (Rect, bool) {
	var rc win32Rect
	ok, _, _ := procGetWindowRect.Call(hwnd, uintptr(unsafe.Pointer(&rc)))
	if ok == 0 {
		return Rect{}, false
	}
	out := rectFromWin32(rc)
	if out.Width() <= 0 || out.Height() <= 0 {
		return Rect{}, false
	}
	return out, true
}

func windowClientScreenRect(hwnd uintptr) (Rect, bool) {
	var client win32Rect
	ok, _, _ := procGetClientRect.Call(hwnd, uintptr(unsafe.Pointer(&client)))
	if ok == 0 {
		return Rect{}, false
	}
	tl := point{X: client.Left, Y: client.Top}
	br := point{X: client.Right, Y: client.Bottom}
	procClientToScreen.Call(hwnd, uintptr(unsafe.Pointer(&tl)))
	procClientToScreen.Call(hwnd, uintptr(unsafe.Pointer(&br)))
	out := Rect{
		Left:   int(tl.X),
		Top:    int(tl.Y),
		Right:  int(br.X),
		Bottom: int(br.Y),
	}
	if out.Width() <= 0 || out.Height() <= 0 {
		return Rect{}, false
	}
	return out, true
}

func isEFTTitle(title string) bool {
	trimmed := strings.TrimSpace(title)
	if trimmed == "" {
		return false
	}
	lower := strings.ToLower(trimmed)
	if strings.Contains(lower, "tarkov") {
		return true
	}
	if strings.Contains(trimmed, "塔科夫") {
		return true
	}
	return strings.Contains(lower, "escape") && strings.Contains(lower, "tarkov")
}
