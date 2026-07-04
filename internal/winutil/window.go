package winutil

import (
	"github.com/wailsapp/wails/v3/pkg/application"

	"bm-tarkov-map-tracker/internal/appmeta"
)

func PrimaryPlacement(app *application.App) (x, y int) {
	x = appmeta.WindowX
	y = appmeta.WindowY
	primary := app.Screen.GetPrimary()
	if primary == nil {
		return x, y
	}
	return primary.WorkArea.X + appmeta.WindowX, primary.WorkArea.Y + appmeta.WindowY
}

func PlaceOnPrimary(window application.Window, app *application.App) {
	px, py := PrimaryPlacement(app)
	window.SetPosition(px, py)
}

func RestoreMainWindow(window application.Window, app *application.App) {
	application.InvokeSync(func() {
		if window.IsMinimised() {
			window.UnMinimise()
		}
		window.Show()
		PlaceOnPrimary(window, app)
		window.Focus()
	})
}
