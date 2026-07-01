package githubupdate

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const defaultTimeout = 15 * time.Second

var titleVersionRe = regexp.MustCompile(`(?i)V(\d+)\.(\d+)(?:\.(\d+))?`)

type ReleaseUpdate struct {
	Major       int
	Minor       int
	Patch       int
	DownloadURL string
}

func ParseVersionTag(tag string) (major, minor, patch int, ok bool) {
	t := strings.TrimSpace(tag)
	if strings.HasPrefix(strings.ToLower(t), "v") {
		t = t[1:]
	}
	parts := strings.Split(t, ".")
	if len(parts) < 2 {
		return 0, 0, 0, false
	}
	var err error
	if major, err = atoi(parts[0]); err != nil {
		return 0, 0, 0, false
	}
	if minor, err = atoi(parts[1]); err != nil {
		return 0, 0, 0, false
	}
	if len(parts) >= 3 {
		if patch, err = atoi(parts[2]); err != nil {
			return 0, 0, 0, false
		}
	}
	return major, minor, patch, true
}

func ParseTitleVersion(suffix string) (major, minor, patch int) {
	m := titleVersionRe.FindStringSubmatch(suffix)
	if len(m) < 3 {
		return 1, 0, 0
	}
	major, _ = atoi(m[1])
	minor, _ = atoi(m[2])
	if len(m) >= 4 && m[3] != "" {
		patch, _ = atoi(m[3])
	}
	return major, minor, patch
}

func VersionLabel(major, minor, patch int) string {
	return fmt.Sprintf("V%d.%d.%d", major, minor, patch)
}

func IsNewer(remoteMajor, remoteMinor, remotePatch, curMajor, curMinor, curPatch int) bool {
	if remoteMajor != curMajor {
		return remoteMajor > curMajor
	}
	if remoteMinor != curMinor {
		return remoteMinor > curMinor
	}
	return remotePatch > curPatch
}

func PickTarkovMapTrackerExe(name string) bool {
	lower := strings.ToLower(name)
	return strings.Contains(lower, "bm-tarkov-map-tracker") &&
		strings.HasSuffix(lower, ".exe") &&
		!strings.Contains(lower, "_win7")
}

func FetchLatestUpdate(repo, userAgent string, currentMajor, currentMinor, currentPatch int, pickAsset func(string) bool) (*ReleaseUpdate, error) {
	if repo == "" || pickAsset == nil {
		return nil, nil
	}
	url := "https://api.github.com/repos/" + repo + "/releases/latest"
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, nil
	}
	req.Header.Set("User-Agent", userAgent)

	client := &http.Client{Timeout: defaultTimeout}
	resp, err := client.Do(req)
	if err != nil {
		return nil, nil
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, nil
	}

	var payload struct {
		TagName string `json:"tag_name"`
		Assets  []struct {
			Name               string `json:"name"`
			BrowserDownloadURL string `json:"browser_download_url"`
		} `json:"assets"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, nil
	}

	major, minor, patch, ok := ParseVersionTag(payload.TagName)
	if !ok || !IsNewer(major, minor, patch, currentMajor, currentMinor, currentPatch) {
		return nil, nil
	}

	var downloadURL string
	for _, asset := range payload.Assets {
		if asset.Name == "" || asset.BrowserDownloadURL == "" {
			continue
		}
		if pickAsset(asset.Name) {
			downloadURL = asset.BrowserDownloadURL
			break
		}
	}
	if downloadURL == "" {
		return nil, nil
	}

	return &ReleaseUpdate{
		Major:       major,
		Minor:       minor,
		Patch:       patch,
		DownloadURL: downloadURL,
	}, nil
}

func BuildSavePath(dir, fileStem string, major, minor, patch int) string {
	label := VersionLabel(major, minor, patch)
	return filepath.Join(dir, fileStem+"-"+label+".exe")
}

func DownloadRelease(url, destPath, userAgent string) error {
	if destPath == "" || url == "" {
		return fmt.Errorf("empty path or url")
	}
	if _, err := os.Stat(destPath); err == nil {
		return nil
	}

	tempPath := destPath + ".download"
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", userAgent)

	client := &http.Client{Timeout: 10 * time.Minute}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("download status %d", resp.StatusCode)
	}

	out, err := os.Create(tempPath)
	if err != nil {
		return err
	}
	_, copyErr := io.Copy(out, resp.Body)
	closeErr := out.Close()
	if copyErr != nil {
		_ = os.Remove(tempPath)
		return copyErr
	}
	if closeErr != nil {
		_ = os.Remove(tempPath)
		return closeErr
	}
	if err := os.Remove(destPath); err != nil && !os.IsNotExist(err) {
		_ = os.Remove(tempPath)
		return err
	}
	return os.Rename(tempPath, destPath)
}

func atoi(s string) (int, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, fmt.Errorf("empty")
	}
	n := 0
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c < '0' || c > '9' {
			return 0, fmt.Errorf("invalid")
		}
		n = n*10 + int(c-'0')
	}
	return n, nil
}
