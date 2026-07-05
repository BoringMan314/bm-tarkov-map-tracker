package embeddedmap

import (
	"sync"
	"sync/atomic"
	"time"

	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"

	"bm-tarkov-map-tracker/internal/gamewin"
)

const (
	gameMissHideThreshold = 50
	gameScanInterval      = 2 * time.Second
	trackerInterval       = 250 * time.Millisecond
)

type Manager struct {
	mu                sync.RWMutex
	app               *application.App
	mainWin           application.Window
	win               application.Window
	settings          Settings
	context           Context
	viewport          *Viewport
	display           DisplayStatus
	gameWindow        GameWindowStatus
	lastGame          gamewin.WindowInfo
	lastAnchor        gamewin.WindowInfo
	gameMiss          int
	overlayShown      bool
	overlayConfigured bool
	lastAppliedBounds application.Rect
	lastGameScan      time.Time
	stop              chan struct{}
	trackerRunning    bool
	pendingSync       atomic.Bool
}

var Default = &Manager{
	settings: DefaultSettings(),
}

func (m *Manager) SetMainWindow(win application.Window) {
	m.mu.Lock()
	m.mainWin = win
	m.mu.Unlock()
}

func (m *Manager) Init(app *application.App) {
	m.app = app
	m.win = app.Window.NewWithOptions(application.WebviewWindowOptions{
		Name:                       "embedded",
		Title:                      "",
		Width:                      300,
		Height:                     300,
		URL:                        "/embedded.html",
		Hidden:                     true,
		Frameless:                  true,
		AlwaysOnTop:                true,
		DisableResize:              true,
		IgnoreMouseEvents:          true,
		BackgroundType:             application.BackgroundTypeTransparent,
		BackgroundColour:           application.NewRGBA(0, 0, 0, 0),
		DefaultContextMenuDisabled: true,
		MinimiseButtonState:        application.ButtonHidden,
		MaximiseButtonState:        application.ButtonHidden,
		CloseButtonState:           application.ButtonHidden,
		MinWidth:                   100,
		MinHeight:                  100,
		Windows: application.WindowsWindow{
			DisableFramelessWindowDecorations: true,
			HiddenOnTaskbar:                   true,
			DisableIcon:                       true,
		},
	})
	m.win.RegisterHook(events.Common.WindowRuntimeReady, func(*application.WindowEvent) {
		m.ActivateSettings()
	})
}

func (m *Manager) Settings() Settings {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.settings
}

func (m *Manager) Context() Context {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.context
}

func (m *Manager) State() StateResponse {
	m.mu.RLock()
	defer m.mu.RUnlock()
	active := m.settings.Position != "none"
	var viewport *Viewport
	if active && m.viewport != nil {
		copy := *m.viewport
		viewport = &copy
	}
	return StateResponse{
		Active:     active,
		Settings:   m.settings,
		Context:    m.context,
		Display:    m.display,
		GameWindow: m.gameWindow,
		Viewport:   viewport,
	}
}

func (m *Manager) SetSettingsQuiet(s Settings) {
	m.mu.Lock()
	m.settings = normalizeSettings(s)
	m.mu.Unlock()
}

func (m *Manager) ActivateSettings() {
	m.mu.RLock()
	active := m.settings.Position != "none"
	m.mu.RUnlock()

	application.InvokeSync(func() {
		m.syncWindow(active)
	})
	if active {
		m.restartTracker()
	} else {
		m.stopTracker()
	}
}

func (m *Manager) ApplySettings(s Settings) {
	m.SetSettingsQuiet(s)
	m.ActivateSettings()
}

func (m *Manager) ApplyContext(ctx Context) {
	m.mu.Lock()
	m.context = ctx
	m.mu.Unlock()
}

func (m *Manager) ApplyViewport(v Viewport) {
	m.mu.Lock()
	if m.settings.Position == "none" {
		m.mu.Unlock()
		return
	}
	copy := v
	m.viewport = &copy
	m.mu.Unlock()
}

func (m *Manager) setStatus(display DisplayStatus, game GameWindowStatus) {
	m.mu.Lock()
	m.display = display
	m.gameWindow = game
	m.mu.Unlock()
}

func (m *Manager) locateGame() (gamewin.WindowInfo, bool) {
	m.mu.RLock()
	lastScan := m.lastGameScan
	cached := m.lastGame
	m.mu.RUnlock()

	if cached.Hwnd != 0 && time.Since(lastScan) < gameScanInterval {
		if refreshed, ok := gamewin.RefreshWindowInfo(cached); ok {
			m.mu.Lock()
			m.lastGame = refreshed
			m.gameMiss = 0
			m.mu.Unlock()
			return refreshed, true
		}
	} else if time.Since(lastScan) < gameScanInterval {
		m.mu.Lock()
		defer m.mu.Unlock()
		m.gameMiss++
		if m.lastGame.Hwnd != 0 && m.gameMiss < gameMissHideThreshold {
			if refreshed, ok := gamewin.RefreshWindowInfo(m.lastGame); ok {
				m.lastGame = refreshed
				return refreshed, true
			}
		}
		return gamewin.WindowInfo{}, false
	}

	if info, ok := gamewin.FindEFTWindow(); ok {
		m.mu.Lock()
		m.lastGame = info
		m.gameMiss = 0
		m.lastGameScan = time.Now()
		m.mu.Unlock()
		return info, true
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	m.gameMiss++
	m.lastGameScan = time.Now()
	if m.lastGame.Hwnd != 0 && m.gameMiss < gameMissHideThreshold {
		if refreshed, ok := gamewin.RefreshWindowInfo(m.lastGame); ok {
			m.lastGame = refreshed
			return refreshed, true
		}
	}
	return gamewin.WindowInfo{}, false
}

func (m *Manager) resolveAnchor() (gamewin.WindowInfo, DisplayStatus, bool) {
	if info, ok := m.locateGame(); ok {
		display := DisplayStatus{
			Target:    "game",
			GameFound: true,
			Title:     info.Title,
			Process:   info.Process,
		}
		m.rememberAnchor(info)
		return info, display, true
	}

	m.mu.RLock()
	mainWin := m.mainWin
	m.mu.RUnlock()
	if info, ok := screenAnchorFromMain(mainWin); ok {
		display := DisplayStatus{Target: "screen", GameFound: false}
		m.rememberAnchor(info)
		return info, display, true
	}

	if info, ok := fallbackWorkAreaAnchor(); ok {
		return info, DisplayStatus{Target: "screen", GameFound: false}, true
	}

	return gamewin.WindowInfo{}, DisplayStatus{Target: "none", GameFound: false}, false
}

func (m *Manager) rememberAnchor(info gamewin.WindowInfo) {
	if info.Rect.Width() <= 0 || info.Rect.Height() <= 0 {
		return
	}
	m.mu.Lock()
	m.lastAnchor = info
	m.mu.Unlock()
}

func (m *Manager) syncWindow(active bool) {
	if m.win == nil {
		return
	}
	if !active {
		m.mu.Lock()
		m.lastGame = gamewin.WindowInfo{}
		m.gameMiss = 0
		m.lastGameScan = time.Time{}
		m.lastAppliedBounds = application.Rect{}
		m.overlayConfigured = false
		m.mu.Unlock()
		m.setStatus(DisplayStatus{Target: "none", GameFound: false}, GameWindowStatus{})
		hideOverlayWindow(m.win)
		m.overlayShown = false
		return
	}

	m.mu.RLock()
	s := m.settings
	m.mu.RUnlock()

	ensureOverlayConfigured(m.win, &m.overlayConfigured)

	anchor, display, ok := m.resolveAnchor()
	gameStatus := GameWindowStatus{Found: display.GameFound}
	if display.Target == "game" {
		gameStatus.Left = anchor.Rect.Left
		gameStatus.Top = anchor.Rect.Top
		gameStatus.Right = anchor.Rect.Right
		gameStatus.Bottom = anchor.Rect.Bottom
		gameStatus.Title = anchor.Title
		gameStatus.Process = anchor.Process
	}
	m.setStatus(display, gameStatus)
	if !ok {
		hideOverlayWindow(m.win)
		m.overlayShown = false
		m.lastAppliedBounds = application.Rect{}
		return
	}
	if showOverlayNoActivate(m.win) {
		m.overlayShown = true
	}
	applyOverlayBounds(m.win, s.Position, s.Size, s.OffsetX, s.OffsetY, anchor, &m.lastAppliedBounds)
}

func (m *Manager) syncWindowPosition() {
	m.mu.RLock()
	s := m.settings
	active := s.Position != "none"
	m.mu.RUnlock()
	if !active || m.win == nil {
		return
	}

	anchor, display, ok := m.resolveAnchor()
	gameStatus := GameWindowStatus{Found: display.GameFound}
	if display.Target == "game" {
		gameStatus.Left = anchor.Rect.Left
		gameStatus.Top = anchor.Rect.Top
		gameStatus.Right = anchor.Rect.Right
		gameStatus.Bottom = anchor.Rect.Bottom
		gameStatus.Title = anchor.Title
		gameStatus.Process = anchor.Process
	}
	m.setStatus(display, gameStatus)
	if !ok {
		hideOverlayWindow(m.win)
		m.overlayShown = false
		m.lastAppliedBounds = application.Rect{}
		return
	}

	if !m.overlayConfigured {
		ensureOverlayConfigured(m.win, &m.overlayConfigured)
	}
	if !m.overlayShown {
		if showOverlayNoActivate(m.win) {
			m.overlayShown = true
		}
	}
	applyOverlayBounds(m.win, s.Position, s.Size, s.OffsetX, s.OffsetY, anchor, &m.lastAppliedBounds)
}

func (m *Manager) restartTracker() {
	m.stopTracker()
	m.startTracker()
}

func (m *Manager) startTracker() {
	m.mu.Lock()
	if m.trackerRunning {
		m.mu.Unlock()
		return
	}
	m.trackerRunning = true
	stop := make(chan struct{})
	m.stop = stop
	m.mu.Unlock()

	go func() {
		ticker := time.NewTicker(trackerInterval)
		defer ticker.Stop()
		for {
			select {
			case <-stop:
				return
			case <-ticker.C:
				if !m.pendingSync.CompareAndSwap(false, true) {
					continue
				}
				application.InvokeAsync(func() {
					defer m.pendingSync.Store(false)
					m.syncWindowPosition()
				})
			}
		}
	}()
}

func (m *Manager) stopTracker() {
	m.mu.Lock()
	if !m.trackerRunning {
		m.mu.Unlock()
		return
	}
	ch := m.stop
	m.trackerRunning = false
	m.stop = nil
	m.mu.Unlock()
	if ch != nil {
		close(ch)
	}
}

func (m *Manager) Shutdown() {
	m.stopTracker()
	application.InvokeSync(func() {
		if m.win == nil {
			return
		}
		hideOverlayWindow(m.win)
		m.overlayShown = false
	})
}
