package watcher

import (
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/fsnotify/fsnotify"

	"bm-tarkov-map-tracker/internal/player"
	"bm-tarkov-map-tracker/internal/screenshots"
)

type Service struct {
	mu   sync.Mutex
	path string
	fsw  *fsnotify.Watcher
}

func New() *Service {
	return &Service{}
}

func DefaultScreenshotsDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ""
	}
	return filepath.Join(home, "Documents", "Escape from Tarkov", "Screenshots")
}

func (s *Service) ScreenshotsPath() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.path != "" {
		return s.path
	}
	return DefaultScreenshotsDir()
}

func (s *Service) SetScreenshotsPath(path string) error {
	path = strings.TrimSpace(path)
	if path == "" {
		path = DefaultScreenshotsDir()
	}
	s.mu.Lock()
	s.path = path
	s.mu.Unlock()
	return s.Restart()
}

func (s *Service) Restart() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.fsw != nil {
		_ = s.fsw.Close()
		s.fsw = nil
	}
	dir := s.path
	if dir == "" {
		dir = DefaultScreenshotsDir()
	}
	if dir == "" {
		return nil
	}
	if err := os.MkdirAll(dir, 0o755); err != nil && !os.IsExist(err) {
		return err
	}
	w, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}
	if err := w.Add(dir); err != nil {
		_ = w.Close()
		return err
	}
	s.fsw = w
	go s.loop(w)
	s.scanExisting(dir)
	return nil
}

func (s *Service) scanExisting(dir string) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return
	}
	var latest string
	var latestMod int64
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if !strings.EqualFold(filepath.Ext(name), ".png") {
			continue
		}
		full := filepath.Join(dir, name)
		if _, ok := screenshots.ParsePath(full); !ok {
			continue
		}
		info, err := entry.Info()
		if err != nil {
			continue
		}
		if info.ModTime().UnixNano() > latestMod {
			latestMod = info.ModTime().UnixNano()
			latest = full
		}
	}
	if latest != "" {
		player.Default.UpdateFromScreenshot(latest)
	}
}

func (s *Service) loop(w *fsnotify.Watcher) {
	for {
		select {
		case ev, ok := <-w.Events:
			if !ok {
				return
			}
			if ev.Op&(fsnotify.Create|fsnotify.Write|fsnotify.Rename) != 0 {
				if strings.EqualFold(filepath.Ext(ev.Name), ".png") {
					player.Default.UpdateFromScreenshot(ev.Name)
				}
			}
		case _, ok := <-w.Errors:
			if !ok {
				return
			}
		}
	}
}

func (s *Service) Stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.fsw != nil {
		_ = s.fsw.Close()
		s.fsw = nil
	}
}
