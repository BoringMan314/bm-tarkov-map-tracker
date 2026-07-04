package gamewin

type Rect struct {
	Left   int
	Top    int
	Right  int
	Bottom int
}

func (r Rect) Width() int {
	if r.Right <= r.Left {
		return 0
	}
	return r.Right - r.Left
}

func (r Rect) Height() int {
	if r.Bottom <= r.Top {
		return 0
	}
	return r.Bottom - r.Top
}

type WindowInfo struct {
	Rect    Rect
	Title   string
	Class   string
	Process string
	Hwnd    uintptr `json:"-"`
}

func FindEFT() (Rect, bool) {
	info, ok := FindEFTWindow()
	if !ok {
		return Rect{}, false
	}
	return info.Rect, true
}

func RefreshWindowInfo(info WindowInfo) (WindowInfo, bool) {
	return refreshWindowInfo(info)
}

func IsWindowValid(hwnd uintptr) bool {
	return isWindowValid(hwnd)
}
