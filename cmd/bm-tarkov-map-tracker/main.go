package main

import (
	"context"
	"io/fs"
	"log"

	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"

	"bm-tarkov-map-tracker/internal/appchrome"
	"bm-tarkov-map-tracker/internal/appmeta"
	"bm-tarkov-map-tracker/internal/apphttp"
	"bm-tarkov-map-tracker/internal/config"
	"bm-tarkov-map-tracker/internal/embeddedmap"
	"bm-tarkov-map-tracker/internal/i18n"
	"bm-tarkov-map-tracker/internal/icons"
	"bm-tarkov-map-tracker/internal/localehttp"
	"bm-tarkov-map-tracker/internal/maps"
	"bm-tarkov-map-tracker/internal/singleinstance"
	"bm-tarkov-map-tracker/internal/watcher"
	"bm-tarkov-map-tracker/internal/winutil"
	rootembed "bm-tarkov-map-tracker"
)

func frontendFS() fs.FS {
	pub, err := rootembed.FrontendPublicFS()
	if err != nil {
		log.Fatal(err)
	}
	return pub
}

func main() {
	if !singleinstance.AcquireOrHandshake() {
		return
	}
	defer singleinstance.Release()

	_ = config.Load()

	watch := watcher.New()
	if err := watch.Restart(); err != nil {
		log.Print(err)
	}
	defer watch.Stop()

	app := application.New(application.Options{
		Name:        appmeta.AppID,
		Description: i18n.WindowTitle(),
		Services: []application.Service{
			application.NewService(NewMapService()),
		},
		Assets: application.AssetOptions{
			Handler: apphttp.Handler(frontendFS()),
		},
		Windows: application.WindowsOptions{
			DisableQuitOnLastWindowClosed: true,
		},
	})

	singleinstance.StartPipeServer(func() {
		application.InvokeSync(func() {
			app.Quit()
		})
	})

	title := i18n.WindowTitle()
	winutil.SetTrackedTitle(title)

	winOpts := application.WebviewWindowOptions{
		Name:                "main",
		Title:               title,
		Width:               appmeta.WindowWidth,
		Height:              appmeta.WindowHeight,
		MinWidth:            appmeta.WindowMinWidth,
		MinHeight:           appmeta.WindowMinHeight,
		DisableResize:       false,
		InitialPosition:     application.WindowXY,
		X:                   appmeta.WindowX,
		Y:                   appmeta.WindowY,
		URL:                 "/",
		BackgroundColour:    application.NewRGB(0, 0, 0),
	}
	if primary := app.Screen.GetPrimary(); primary != nil {
		winOpts.Screen = primary
	}
	window := app.Window.NewWithOptions(winOpts)
	embeddedmap.Default.Init(app)
	embeddedmap.Default.SetMainWindow(window)
	embeddedmap.PersistSettings = config.SaveEmbeddedMapSettings
	embeddedmap.Default.SetSettingsQuiet(config.StoredEmbeddedMapSettings())

	window.RegisterHook(events.Common.WindowMinimise, func(e *application.WindowEvent) {
		window.Hide()
	})

	window.RegisterHook(events.Common.WindowClosing, func(e *application.WindowEvent) {
		app.Quit()
	})

	systray := app.SystemTray.New()
	if iconData := icons.LoadTrayPNG(); len(iconData) > 0 {
		systray.SetIcon(iconData)
		app.SetIcon(iconData)
	}
	systray.SetTooltip(title)

	restore := func() {
		winutil.RestoreMainWindow(window, app)
	}

	chrome := appchrome.New(app, window, systray, restore)
	chrome.BuildTrayMenu()

	refreshChrome := func() {
		chrome.RefreshLocale()
	}

	localehttp.SetOnChange(refreshChrome)

	systray.OnClick(func() {
		restore()
	})

	app.OnShutdown(func() {
		embeddedmap.Default.Shutdown()
		chrome.Shutdown()
		systray.Destroy()
	})

	chrome.StartUpdateCheck()

	if err := app.Run(); err != nil {
		log.Fatal(err)
	}
}

type MapService struct{}

func NewMapService() *MapService {
	return &MapService{}
}

func (m *MapService) ListMaps() ([]maps.Entry, error) {
	return maps.List()
}

func (m *MapService) startup(_ context.Context) {}
