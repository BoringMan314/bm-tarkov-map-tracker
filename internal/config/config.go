package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"

	"bm-tarkov-map-tracker/internal/appmeta"
	"bm-tarkov-map-tracker/internal/i18n"
)

type Settings struct {
	Languages string                  `json:"languages"`
	Embedded  EmbeddedMapFileSettings `json:"embedded,omitempty"`
}

type File struct {
	Settings  Settings                    `json:"settings"`
	Languages map[string]i18n.LocaleTable `json:"languages"`
}

func ConfigPath() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	return filepath.Join(filepath.Dir(exe), appmeta.ConfigFileName), nil
}

func Load() error {
	path, err := ConfigPath()
	if err != nil {
		applyDefaults()
		return nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Save(Defaults())
		}
		return Save(Defaults())
	}
	var file File
	if err := json.Unmarshal(data, &file); err != nil {
		_ = os.Remove(path)
		return Save(Defaults())
	}
	file = mergeMissingKeys(file)
	if !validate(&file) {
		_ = os.Remove(path)
		return Save(Defaults())
	}
	i18n.SetTables(file.Languages, file.Settings.Languages)
	return nil
}

func Save(file File) error {
	path, err := ConfigPath()
	if err != nil {
		return err
	}
	data, err := json.MarshalIndent(file, "", "  ")
	if err != nil {
		return err
	}
	i18n.SetTables(file.Languages, file.Settings.Languages)
	return os.WriteFile(path, data, 0644)
}

func Defaults() File {
	tables := i18n.BuiltinTables()
	return File{
		Settings: Settings{
			Languages: "zh_TW",
			Embedded:  defaultEmbeddedMapFileSettings(),
		},
		Languages: tables,
	}
}

func validate(file *File) bool {
	if file == nil {
		return false
	}
	if file.Settings.Languages == "" {
		return false
	}
	if len(file.Languages) == 0 {
		return false
	}
	active, ok := file.Languages[file.Settings.Languages]
	if !ok {
		return false
	}
	required := i18n.BuiltinTables()["zh_TW"]
	for key, want := range required {
		got, ok := active[key]
		if !ok || got == "" {
			return false
		}
		_ = want
	}
	for code, table := range file.Languages {
		for key := range required {
			if _, ok := table[key]; !ok {
				return false
			}
			if table[key] == "" {
				return false
			}
		}
		_ = code
	}
	return true
}

func SetActiveLocale(code string) error {
	path, err := ConfigPath()
	if err != nil {
		return err
	}
	var file File
	data, err := os.ReadFile(path)
	if err != nil {
		file = Defaults()
	} else if err := json.Unmarshal(data, &file); err != nil {
		file = Defaults()
	}
	if _, ok := file.Languages[code]; !ok {
		return os.ErrInvalid
	}
	file = mergeMissingKeys(file)
	file.Settings.Languages = code
	return Save(file)
}

func mergeMissingKeys(file File) File {
	builtinTables := i18n.BuiltinTables()
	required := builtinTables["zh_TW"]
	for code, builtinTable := range builtinTables {
		table, ok := file.Languages[code]
		if !ok {
			copyTable := make(i18n.LocaleTable, len(builtinTable))
			for k, v := range builtinTable {
				copyTable[k] = v
			}
			file.Languages[code] = copyTable
			continue
		}
		for key, val := range builtinTable {
			if strings.HasPrefix(key, "map_") || strings.HasPrefix(key, "exfil_") || strings.HasPrefix(key, "marker_") || strings.HasPrefix(key, "embedded_") {
				table[key] = val
				continue
			}
			if _, ok := table[key]; !ok || table[key] == "" {
				table[key] = val
			}
		}
		for key := range required {
			if _, ok := table[key]; !ok {
				table[key] = builtinTable[key]
			}
		}
		file.Languages[code] = table
	}
	return file
}

func applyDefaults() {
	def := Defaults()
	i18n.SetTables(def.Languages, def.Settings.Languages)
}
