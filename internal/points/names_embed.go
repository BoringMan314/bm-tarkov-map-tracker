package points

import (
	"embed"
)

//go:embed exfil_names.json eftarkov_names.json
var namesFS embed.FS
