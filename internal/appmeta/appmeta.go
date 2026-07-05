package appmeta

const (
	AppID           = "bm-tarkov-map-tracker"
	ConfigFileName  = "bm-tarkov-map-tracker.json"
	CurrentVersion  = "0.2"
	RepositoryURL   = "https://github.com/BoringMan314/bm-tarkov-map-tracker"
	GitHubRepo      = "BoringMan314/bm-tarkov-map-tracker"
	UpdateUserAgent = "bm-tarkov-map-tracker"
	ExeFileStem     = "bm-tarkov-map-tracker"
	AboutURL        = "http://exnormal.com:81/"
	TitlePrefix     = "[B.M] "
	TitleSuffix     = " V0.2 By. [B.M] 圓周率 3.14"
	WindowX         = 100
	WindowY         = 100
	WindowWidth     = 1000
	WindowHeight    = 700
	WindowMinWidth  = 640
	WindowMinHeight = 480
	DefaultMap      = "woods"
)

func WindowTitle(projectName string) string {
	return TitlePrefix + projectName + TitleSuffix
}
