//go:build windows

package singleinstance

import (
	"sync"
	"time"

	"golang.org/x/sys/windows"
)

const (
	appID              = "bm-tarkov-map-tracker"
	pipeSignalByte     = 0x7E
	mutexWaitMS        = uint32(120000)
	notifyRetries      = 100
	notifyDelay        = 50 * time.Millisecond
	errorPipeConnected = windows.ERROR_PIPE_CONNECTED
)

var (
	mutexHandle windows.Handle
	stopPipe    chan struct{}
	pipeOnce    sync.Once
	releaseOnce sync.Once
)

func MutexName() string {
	return `Global\` + appID
}

func PipePath() string {
	return `\\.\pipe\` + appID
}

func AcquireOrHandshake() bool {
	name, err := windows.UTF16PtrFromString(MutexName())
	if err != nil {
		return false
	}
	h, err := windows.CreateMutex(nil, true, name)
	if h == 0 {
		return false
	}
	if err == windows.ERROR_ALREADY_EXISTS {
		notifyPeerToQuit()
		w, waitErr := windows.WaitForSingleObject(h, mutexWaitMS)
		if waitErr != nil || (w != windows.WAIT_OBJECT_0 && w != windows.WAIT_ABANDONED) {
			windows.CloseHandle(h)
			return false
		}
	}
	mutexHandle = h
	return true
}

func Release() {
	releaseOnce.Do(func() {
		if mutexHandle != 0 {
			windows.ReleaseMutex(mutexHandle)
			windows.CloseHandle(mutexHandle)
			mutexHandle = 0
		}
		if stopPipe != nil {
			close(stopPipe)
			stopPipe = nil
		}
	})
}

func StartPipeServer(onQuit func()) {
	pipeOnce.Do(func() {
		stopPipe = make(chan struct{})
		go pipeWorker(onQuit)
	})
}

func notifyPeerToQuit() {
	path, err := windows.UTF16PtrFromString(PipePath())
	if err != nil {
		return
	}
	for i := 0; i < notifyRetries; i++ {
		h, err := windows.CreateFile(
			path,
			windows.GENERIC_READ|windows.GENERIC_WRITE,
			0,
			nil,
			windows.OPEN_EXISTING,
			0,
			0,
		)
		if err == nil && h != windows.InvalidHandle {
			buf := []byte{pipeSignalByte}
			var written uint32
			_ = windows.WriteFile(h, buf, &written, nil)
			_ = windows.CloseHandle(h)
			return
		}
		time.Sleep(notifyDelay)
	}
}

func pipeWorker(onQuit func()) {
	path, err := windows.UTF16PtrFromString(PipePath())
	if err != nil {
		return
	}
	for {
		select {
		case <-stopPipe:
			return
		default:
		}
		pipe, err := windows.CreateNamedPipe(
			path,
			windows.PIPE_ACCESS_DUPLEX,
			windows.PIPE_TYPE_BYTE|windows.PIPE_READMODE_BYTE,
			255,
			1024,
			1024,
			0,
			nil,
		)
		if err != nil {
			time.Sleep(200 * time.Millisecond)
			continue
		}
		connErr := windows.ConnectNamedPipe(pipe, nil)
		if connErr != nil && connErr != errorPipeConnected {
			_ = windows.CloseHandle(pipe)
			time.Sleep(50 * time.Millisecond)
			continue
		}
		buf := make([]byte, 4)
		var read uint32
		_ = windows.ReadFile(pipe, buf, &read, nil)
		_ = windows.DisconnectNamedPipe(pipe)
		_ = windows.CloseHandle(pipe)
		if onQuit != nil {
			onQuit()
		}
	}
}
