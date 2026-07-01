//go:build !windows

package winutil

func SetTrackedTitle(string) {}

func ActivateTracked(x, y int) {}