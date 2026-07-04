package appchrome

import (
	"strings"
	"sync"
	"time"

	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/appmeta"
	"bm-tarkov-map-tracker/internal/githubupdate"
	"bm-tarkov-map-tracker/internal/i18n"
	"bm-tarkov-map-tracker/internal/winutil"
)

type Chrome struct {
	app     *application.App
	window  application.Window
	systray *application.SystemTray
	restore func()

	mu             sync.Mutex
	updateInfo     *githubupdate.ReleaseUpdate
	checkStarted   bool
	titleAlt       bool
	titleAfterStop chan struct{}
}

func New(app *application.App, window application.Window, systray *application.SystemTray, restore func()) *Chrome {
	return &Chrome{
		app:            app,
		window:         window,
		systray:        systray,
		restore:        restore,
		titleAfterStop: make(chan struct{}),
	}
}

func (c *Chrome) BaseTitle() string {
	return i18n.WindowTitle()
}

func (c *Chrome) UpdateAvailableTitle() string {
	c.mu.Lock()
	info := c.updateInfo
	c.mu.Unlock()
	if info == nil {
		return c.BaseTitle()
	}
	label := githubupdate.VersionLabel(info.Major, info.Minor, info.Patch)
	text := i18n.T("update_available_title")
	return strings.ReplaceAll(text, "{version}", label)
}

func (c *Chrome) WindowTitle() string {
	c.mu.Lock()
	alt := c.titleAlt && c.updateInfo != nil
	c.mu.Unlock()
	if alt {
		return c.UpdateAvailableTitle()
	}
	return c.BaseTitle()
}

func (c *Chrome) ApplyWindowTitle() {
	title := c.WindowTitle()
	winutil.SetTrackedTitle(title)
	application.InvokeSync(func() {
		c.window.SetTitle(title)
	})
}

func (c *Chrome) RefreshLocale() {
	application.InvokeSync(func() {
		c.systray.SetTooltip(c.BaseTitle())
		c.ApplyWindowTitle()
		c.BuildTrayMenu()
	})
}

func (c *Chrome) StartUpdateCheck() {
	c.mu.Lock()
	if c.checkStarted {
		c.mu.Unlock()
		return
	}
	c.checkStarted = true
	c.mu.Unlock()

	go func() {
		curMajor, curMinor, curPatch := githubupdate.ParseTitleVersion(appmeta.TitleSuffix)
		info, _ := githubupdate.FetchLatestUpdate(
			appmeta.GitHubRepo,
			appmeta.UpdateUserAgent,
			curMajor, curMinor, curPatch,
			githubupdate.PickTarkovMapTrackerExe,
		)
		if info == nil {
			return
		}
		application.InvokeSync(func() {
			c.onUpdateAvailable(info)
		})
	}()
}

func (c *Chrome) onUpdateAvailable(info *githubupdate.ReleaseUpdate) {
	c.mu.Lock()
	c.updateInfo = info
	c.mu.Unlock()
	c.startTitleAlternation()
	c.BuildTrayMenu()
}

func (c *Chrome) startTitleAlternation() {
	c.stopTitleAlternation()
	go func() {
		ticker := time.NewTicker(3 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-c.titleAfterStop:
				return
			case <-ticker.C:
				c.mu.Lock()
				if c.updateInfo == nil {
					c.mu.Unlock()
					return
				}
				c.titleAlt = !c.titleAlt
				c.mu.Unlock()
				c.ApplyWindowTitle()
			}
		}
	}()
}

func (c *Chrome) stopTitleAlternation() {
	select {
	case c.titleAfterStop <- struct{}{}:
	default:
	}
	c.titleAfterStop = make(chan struct{})
	c.mu.Lock()
	c.titleAlt = false
	c.mu.Unlock()
}

func (c *Chrome) Shutdown() {
	c.stopTitleAlternation()
}

func (c *Chrome) BuildTrayMenu() {
	menu := c.app.NewMenu()
	menu.Add(i18n.T("tray_restore")).SetHidden(true).OnClick(func(ctx *application.Context) {
		c.restore()
	})

	c.mu.Lock()
	info := c.updateInfo
	c.mu.Unlock()

	if info != nil {
		menu.Add(i18n.T("download_update")).OnClick(func(ctx *application.Context) {
			c.downloadUpdate()
		})
	}

	menu.Add("GitHub").OnClick(func(ctx *application.Context) {
		_ = c.app.Browser.OpenURL(appmeta.RepositoryURL)
	})
	menu.Add(i18n.T("about")).OnClick(func(ctx *application.Context) {
		_ = c.app.Browser.OpenURL(appmeta.AboutURL)
	})
	menu.Add(i18n.T("exit")).OnClick(func(ctx *application.Context) {
		c.app.Quit()
	})
	c.systray.SetMenu(menu)
}

func (c *Chrome) downloadUpdate() {
	c.mu.Lock()
	info := c.updateInfo
	c.mu.Unlock()
	if info == nil || info.DownloadURL == "" {
		return
	}
	url := info.DownloadURL
	application.InvokeSync(func() {
		_ = c.app.Browser.OpenURL(url)
		c.app.Quit()
	})
}
