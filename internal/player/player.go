package player

import (
	"sync"

	"bm-tarkov-map-tracker/internal/screenshots"
)

type Location struct {
	Valid    bool    `json:"valid"`
	X        float64 `json:"x"`
	Y        float64 `json:"y"`
	Z        float64 `json:"z"`
	Rotation float64 `json:"rotation"`
}

type Service struct {
	mu       sync.RWMutex
	self     Location
	username string
}

var Default = &Service{
	self: Location{Valid: true, X: 0, Y: 0, Z: 0, Rotation: 0},
}

func (s *Service) SetUsername(name string) {
	s.mu.Lock()
	s.username = name
	s.mu.Unlock()
}

func (s *Service) Username() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.username
}

func (s *Service) UpdateFromScreenshot(path string) bool {
	data, ok := screenshots.ParsePath(path)
	if !ok {
		return false
	}
	loc := Location{
		Valid:    true,
		X:        data.X,
		Y:        data.Y,
		Z:        data.Z,
		Rotation: screenshots.YawDegrees(data.Qx, data.Qy, data.Qz, data.Qw),
	}
	s.mu.Lock()
	s.self = loc
	s.mu.Unlock()
	return true
}

func (s *Service) Self() Location {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.self
}

func (s *Service) Clear() {
	s.mu.Lock()
	s.self = Location{}
	s.mu.Unlock()
}
