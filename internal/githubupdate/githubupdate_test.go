package githubupdate

import "testing"

func TestParseVersionTag(t *testing.T) {
	maj, min, patch, ok := ParseVersionTag("v1.0.1")
	if !ok || maj != 1 || min != 0 || patch != 1 {
		t.Fatalf("v1.0.1 => %v %d.%d.%d", ok, maj, min, patch)
	}
	_, _, _, ok = ParseVersionTag("1.0")
	if !ok {
		t.Fatal("1.0 should parse with patch 0")
	}
}

func TestParseTitleVersion(t *testing.T) {
	maj, min, patch := ParseTitleVersion(" V0.1 By. [B.M] 圓周率 3.14")
	if maj != 0 || min != 1 || patch != 0 {
		t.Fatalf("got %d.%d.%d", maj, min, patch)
	}
}

func TestIsNewer(t *testing.T) {
	if !IsNewer(1, 0, 1, 1, 0, 0) {
		t.Fatal("1.0.1 should be newer than 1.0.0")
	}
	if IsNewer(1, 0, 0, 1, 0, 0) {
		t.Fatal("1.0.0 should not be newer than 1.0.0")
	}
}

func TestPickTarkovMapTrackerExe(t *testing.T) {
	if !PickTarkovMapTrackerExe("bm-tarkov-map-tracker.exe") {
		t.Fatal("expected main exe")
	}
	if PickTarkovMapTrackerExe("bm-tarkov-map-tracker_win7.exe") {
		t.Fatal("win7 exe should be rejected")
	}
}

func TestBuildSavePath(t *testing.T) {
	got := BuildSavePath(`C:\apps`, "bm-tarkov-map-tracker", 1, 2, 3)
	want := `C:\apps\bm-tarkov-map-tracker-V1.2.3.exe`
	if got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}
