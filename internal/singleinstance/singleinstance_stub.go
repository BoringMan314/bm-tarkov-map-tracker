//go:build !windows

package singleinstance

func AcquireOrHandshake() bool {
	return true
}

func Release() {}

func StartPipeServer(onQuit func()) {}
