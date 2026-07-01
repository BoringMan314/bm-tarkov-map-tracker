package maps

import (
	"regexp"
	"strconv"
)

var viewBoxRe = regexp.MustCompile(`viewBox=["']([^"']+)["']`)

func parseViewBox(raw string) (width, height float64, ok bool) {
	var parts []float64
	cur := ""
	for _, ch := range raw {
		if ch == ' ' || ch == ',' || ch == '\t' || ch == '\n' || ch == '\r' {
			if cur != "" {
				if v, err := strconv.ParseFloat(cur, 64); err == nil {
					parts = append(parts, v)
				}
				cur = ""
			}
			continue
		}
		cur += string(ch)
	}
	if cur != "" {
		if v, err := strconv.ParseFloat(cur, 64); err == nil {
			parts = append(parts, v)
		}
	}
	if len(parts) != 4 || parts[2] <= 0 || parts[3] <= 0 {
		return 0, 0, false
	}
	return parts[2], parts[3], true
}

func diff(a, b float64) float64 {
	if a > b {
		return a - b
	}
	return b - a
}
