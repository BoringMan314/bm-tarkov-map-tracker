package screenshots_test

import (
	"testing"

	"bm-tarkov-map-tracker/internal/screenshots"
)

func TestParsePathLegacy(t *testing.T) {
	data, ok := screenshots.ParsePath(`C:\Screenshots\2024-06-25_14-30_45.2,-123.4,67.8_0.1,-0.2,0.3,0.9.png`)
	if !ok {
		t.Fatal("expected ok")
	}
	if data.X != 45.2 || data.Y != -123.4 || data.Z != 67.8 {
		t.Fatalf("pos mismatch: %+v", data)
	}
	if data.Qx != 0.1 || data.Qy != -0.2 || data.Qz != 0.3 || data.Qw != 0.9 {
		t.Fatalf("quat mismatch: %+v", data)
	}
	yaw := screenshots.YawDegrees(data.Qx, data.Qy, data.Qz, data.Qw)
	if yaw < 0 || yaw > 360 {
		t.Fatalf("yaw out of range: %v", yaw)
	}
}

func TestParsePathBracketFormat(t *testing.T) {
	path := `C:\Users\me\Documents\Escape from Tarkov\Screenshots\2026-07-01[22-50]_-43.16, 2.60, 39.05_-0.00052, 0.99876, -0.04866, -0.01058_15.47 (0).png`
	data, ok := screenshots.ParsePath(path)
	if !ok {
		t.Fatal("expected ok")
	}
	if data.X != -43.16 || data.Y != 2.60 || data.Z != 39.05 {
		t.Fatalf("pos mismatch: %+v", data)
	}
	if data.Qx != -0.00052 || data.Qy != 0.99876 || data.Qz != -0.04866 || data.Qw != -0.01058 {
		t.Fatalf("quat mismatch: %+v", data)
	}
}

func TestParsePathSkipsPlainScreenshot(t *testing.T) {
	_, ok := screenshots.ParsePath(`C:\Screenshots\2026-07-01[22-48] (0).png`)
	if ok {
		t.Fatal("expected plain screenshot to fail parse")
	}
}
