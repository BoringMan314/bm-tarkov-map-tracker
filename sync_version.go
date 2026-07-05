//go:build ignore

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
)

func main() {
	version := "0.2"
	writeWindowsInfoJSON(version)
	updateConfigYML(version)
}

func writeWindowsInfoJSON(version string) {
	product := fmt.Sprintf("[B.M] 塔科夫地圖追蹤 V%s By. [B.M] 圓周率 3.14", version)
	path := filepath.Join("build", "windows", "info.json")
	content := fmt.Sprintf(`{
  "fixed": {
    "file_version": "%[1]s.0",
    "product_version": "%[1]s.0"
  },
  "info": {
    "0409": {
      "ProductVersion": "%[1]s.0",
      "CompanyName": "[B.M] 圓周率 3.14",
      "FileDescription": "%[2]s",
      "LegalCopyright": "[B.M] 圓周率 3.14",
      "ProductName": "%[2]s",
      "Comments": "bm-tarkov-map-tracker",
      "InternalName": "bm-tarkov-map-tracker",
      "OriginalFilename": "bm-tarkov-map-tracker.exe"
    }
  }
}
`, version, product)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		fmt.Fprintf(os.Stderr, "mkdir: %v\n", err)
		os.Exit(1)
	}
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		fmt.Fprintf(os.Stderr, "write info.json: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("wrote %s\n", path)
}

func updateConfigYML(version string) {
	path := filepath.Join("build", "config.yml")
	data, err := os.ReadFile(path)
	if err != nil {
		return
	}
	product := fmt.Sprintf("[B.M] 塔科夫地圖追蹤 V%s By. [B.M] 圓周率 3.14", version)
	out := string(data)
	out = replaceYAMLValue(out, "companyName", "[B.M] 圓周率 3.14")
	out = replaceYAMLValue(out, "productName", product)
	out = replaceYAMLValue(out, "productIdentifier", "com.bm.tarkov-map-tracker")
	out = replaceYAMLValue(out, "description", product)
	out = replaceYAMLValue(out, "copyright", "[B.M] 圓周率 3.14")
	out = replaceYAMLValue(out, "comments", "bm-tarkov-map-tracker")
	out = replaceYAMLValue(out, "version", version)
	if err := os.WriteFile(path, []byte(out), 0644); err != nil {
		fmt.Fprintf(os.Stderr, "write config.yml: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("updated %s\n", path)
}

func replaceYAMLValue(s, key, value string) string {
	re := regexp.MustCompile(`(?m)^(\s*` + regexp.QuoteMeta(key) + `:\s*").*(")\s*$`)
	return re.ReplaceAllString(s, `${1}`+value+`${2}`)
}
