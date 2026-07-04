package config

import (
	"encoding/json"
	"os"

	"bm-tarkov-map-tracker/internal/embeddedmap"
)

type EmbeddedMapFileSettings struct {
	Position string `json:"position,omitempty"`
	Range    int    `json:"range,omitempty"`
	Size     int    `json:"size,omitempty"`
	Offset   int    `json:"offset,omitempty"`
	OffsetX  int    `json:"offsetX,omitempty"`
	OffsetY  int    `json:"offsetY,omitempty"`
	Opacity  int    `json:"opacity,omitempty"`
}

func defaultEmbeddedMapFileSettings() EmbeddedMapFileSettings {
	return embeddedMapFileSettingsFrom(embeddedmap.DefaultSettings())
}

func embeddedMapFileSettingsFrom(s embeddedmap.Settings) EmbeddedMapFileSettings {
	return EmbeddedMapFileSettings{
		Position: s.Position,
		Range:    s.Range,
		Size:     s.Size,
		OffsetX:  s.OffsetX,
		OffsetY:  s.OffsetY,
		Opacity:  s.Opacity,
	}
}

func embeddedMapSettingsFromFile(s EmbeddedMapFileSettings) embeddedmap.Settings {
	offsetX := s.OffsetX
	offsetY := s.OffsetY
	if s.Offset != 0 && offsetX == 0 && offsetY == 0 {
		offsetX = s.Offset
	}
	return embeddedmap.NormalizeSettings(embeddedmap.Settings{
		Position: s.Position,
		Range:    s.Range,
		Size:     s.Size,
		OffsetX:  offsetX,
		OffsetY:  offsetY,
		Opacity:  s.Opacity,
	})
}

func readConfigFile() (File, error) {
	path, err := ConfigPath()
	if err != nil {
		return Defaults(), err
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return Defaults(), err
	}
	var file File
	if err := json.Unmarshal(data, &file); err != nil {
		return Defaults(), err
	}
	return mergeMissingKeys(file), nil
}

func StoredEmbeddedMapSettings() embeddedmap.Settings {
	file, err := readConfigFile()
	if err != nil || file.Settings.Embedded.Position == "" {
		return embeddedmap.DefaultSettings()
	}
	return embeddedMapSettingsFromFile(file.Settings.Embedded)
}

func SaveEmbeddedMapSettings(s embeddedmap.Settings) error {
	file, err := readConfigFile()
	if err != nil {
		if os.IsNotExist(err) {
			file = Defaults()
		} else {
			file = Defaults()
		}
	}
	file.Settings.Embedded = embeddedMapFileSettingsFrom(embeddedmap.NormalizeSettings(s))
	return Save(file)
}
