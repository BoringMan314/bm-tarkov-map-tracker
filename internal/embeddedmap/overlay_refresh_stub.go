//go:build !windows

package embeddedmap

import "github.com/wailsapp/wails/v3/pkg/application"

func refreshOverlayTransparency(application.Window) {}
