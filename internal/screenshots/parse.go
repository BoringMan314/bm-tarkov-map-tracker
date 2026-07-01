package screenshots

import (
	"math"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
)

type Data struct {
	X  float64
	Y  float64
	Z  float64
	Qx float64
	Qy float64
	Qz float64
	Qw float64
}

var duplicateSuffix = regexp.MustCompile(` \(\d+\)$`)

func ParsePath(path string) (Data, bool) {
	base := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
	base = duplicateSuffix.ReplaceAllString(base, "")
	parts := strings.Split(base, "_")
	if len(parts) < 3 {
		return Data{}, false
	}

	var posStr, viewStr string
	switch {
	case strings.Contains(parts[0], "[") && strings.Contains(parts[0], "]"):
		// YYYY-MM-DD[HH-MM]_X,Y,Z_Qx,Qy,Qz,Qw_...
		posStr = parts[1]
		viewStr = parts[2]
	case len(parts) >= 4:
		// YYYY-MM-DD_HH-MM_X,Y,Z_Qx,Qy,Qz,Qw
		posStr = parts[2]
		viewStr = parts[3]
	default:
		return Data{}, false
	}

	pos := strings.Split(posStr, ",")
	view := strings.Split(viewStr, ",")
	if len(pos) != 3 || len(view) != 4 {
		return Data{}, false
	}
	x, errX := strconv.ParseFloat(strings.TrimSpace(pos[0]), 64)
	y, errY := strconv.ParseFloat(strings.TrimSpace(pos[1]), 64)
	z, errZ := strconv.ParseFloat(strings.TrimSpace(pos[2]), 64)
	qx, errQx := strconv.ParseFloat(strings.TrimSpace(view[0]), 64)
	qy, errQy := strconv.ParseFloat(strings.TrimSpace(view[1]), 64)
	qz, errQz := strconv.ParseFloat(strings.TrimSpace(view[2]), 64)
	qw, errQw := strconv.ParseFloat(strings.TrimSpace(view[3]), 64)
	if errX != nil || errY != nil || errZ != nil || errQx != nil || errQy != nil || errQz != nil || errQw != nil {
		return Data{}, false
	}
	return Data{X: x, Y: y, Z: z, Qx: qx, Qy: qy, Qz: qz, Qw: qw}, true
}

func YawDegrees(qx, qy, qz, qw float64) float64 {
	siny := 2 * (qw*qy + qx*qz)
	cosy := 1 - 2*(qy*qy+qz*qz)
	yaw := math.Atan2(siny, cosy) * 180 / math.Pi
	if yaw < 0 {
		yaw += 360
	}
	return yaw
}
