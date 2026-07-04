package rootembed

import (
	"embed"
	"io/fs"
)

//go:embed all:maps all:points all:icons all:i18n
var game embed.FS

//go:embed all:frontend/public
var frontend embed.FS

func GameFS() embed.FS {
	return game
}

func I18nFS() fs.FS {
	sub, err := fs.Sub(game, "i18n")
	if err != nil {
		panic(err)
	}
	return sub
}

func FrontendPublicFS() (fs.FS, error) {
	return fs.Sub(frontend, "frontend/public")
}
