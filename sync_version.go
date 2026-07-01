//go:build ignore

package main

import (
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	version := "0.1"
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
	replacements := []struct {
		old string
		new string
	}{
		{`companyName: "My Company"`, `companyName: "[B.M] 圓周率 3.14"`},
		{`productName: "My Product"`, fmt.Sprintf(`productName: "%s"`, product)},
		{`productIdentifier: "com.mycompany.myproduct"`, `productIdentifier: "com.bm.tarkov-map-tracker"`},
		{`description: "A program that does X"`, fmt.Sprintf(`description: "%s"`, product)},
		{`copyright: "(c) 2025, My Company"`, `copyright: "[B.M] 圓周率 3.14"`},
		{`comments: "Some Product Comments"`, `comments: "bm-tarkov-map-tracker"`},
		{`version: "1.0.0"`, fmt.Sprintf(`version: "%s"`, version)},
	}
	out := string(data)
	for _, r := range replacements {
		out = replaceOnce(out, r.old, r.new)
	}
	if err := os.WriteFile(path, []byte(out), 0644); err != nil {
		fmt.Fprintf(os.Stderr, "write config.yml: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("updated %s\n", path)
}

func replaceOnce(s, old, new string) string {
	if old == "" {
		return s
	}
	idx := -1
	for i := 0; i <= len(s)-len(old); i++ {
		if s[i:i+len(old)] == old {
			idx = i
			break
		}
	}
	if idx < 0 {
		return s
	}
	return s[:idx] + new + s[idx+len(old):]
}
