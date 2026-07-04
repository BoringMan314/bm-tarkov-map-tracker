package embeddedmap

type Settings struct {
	Position string `json:"position"`
	Range    int    `json:"range"`
	Size     int    `json:"size"`
	OffsetX  int    `json:"offsetX"`
	OffsetY  int    `json:"offsetY"`
	Opacity  int    `json:"opacity"`
}

type Context struct {
	MapID       string `json:"mapId"`
	PointSource string `json:"pointSource"`
}

type PlayerMarker struct {
	X       float64 `json:"x"`
	Y       float64 `json:"y"`
	Heading float64 `json:"heading"`
	ImgRot  float64 `json:"imgRot,omitempty"`
	GameX   float64 `json:"gameX,omitempty"`
	GameZ   float64 `json:"gameZ,omitempty"`
}

type OverlayMarker struct {
	Kind   string  `json:"kind"`
	X      float64 `json:"x"`
	Y      float64 `json:"y"`
	Icon   string  `json:"icon,omitempty"`
	Color  string  `json:"color,omitempty"`
	Name   string  `json:"name,omitempty"`
	GameX  float64 `json:"gameX,omitempty"`
	GameZ  float64 `json:"gameZ,omitempty"`
	ZIndex int     `json:"zIndex,omitempty"`
}

type Viewport struct {
	Scale      float64         `json:"scale"`
	Tx         float64         `json:"tx"`
	Ty         float64         `json:"ty"`
	Rotation   float64         `json:"rotation"`
	IW         float64         `json:"iw"`
	IH         float64         `json:"ih"`
	MapURL     string          `json:"mapUrl"`
	ShowNames  bool            `json:"showNames"`
	ShowCoords bool            `json:"showCoords"`
	ShowPlayer bool            `json:"showPlayer"`
	Markers    []OverlayMarker `json:"markers,omitempty"`
	Player     *PlayerMarker   `json:"player,omitempty"`
}

type DisplayStatus struct {
	Target    string `json:"target"`
	GameFound bool   `json:"gameFound"`
	Title     string `json:"title,omitempty"`
	Process   string `json:"process,omitempty"`
}

type GameWindowStatus struct {
	Found   bool   `json:"found"`
	Left    int    `json:"left,omitempty"`
	Top     int    `json:"top,omitempty"`
	Right   int    `json:"right,omitempty"`
	Bottom  int    `json:"bottom,omitempty"`
	Title   string `json:"title,omitempty"`
	Process string `json:"process,omitempty"`
}

type StateResponse struct {
	Active     bool             `json:"active"`
	Settings   Settings         `json:"settings"`
	Context    Context          `json:"context"`
	Display    DisplayStatus    `json:"display"`
	GameWindow GameWindowStatus `json:"gameWindow"`
	Viewport   *Viewport        `json:"viewport,omitempty"`
}

func DefaultSettings() Settings {
	return Settings{
		Position: "none",
		Range:    10,
		Size:     300,
		OffsetX:  250,
		OffsetY:  0,
		Opacity:  50,
	}
}

func NormalizeSettings(s Settings) Settings {
	return normalizeSettings(s)
}

func normalizeSettings(s Settings) Settings {
	out := DefaultSettings()
	switch s.Position {
	case "none", "top-left", "top-right", "bottom-left", "bottom-right":
		out.Position = s.Position
	}
	switch s.Range {
	case 1, 5, 10, 15, 20:
		out.Range = s.Range
	}
	switch s.Size {
	case 100, 200, 300:
		out.Size = s.Size
	}
	switch s.OffsetX {
	case 0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500:
		out.OffsetX = s.OffsetX
	}
	switch s.OffsetY {
	case 0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500:
		out.OffsetY = s.OffsetY
	}
	switch s.Opacity {
	case 0, 30, 50, 80:
		out.Opacity = s.Opacity
	}
	return out
}
