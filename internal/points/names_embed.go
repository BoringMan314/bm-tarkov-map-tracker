package points

import (
	"embed"
)

//go:embed exfil/names.json eftarkov/names.json
var namesFS embed.FS
