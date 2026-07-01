package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	rootembed "bm-tarkov-map-tracker"
)

func TestFrontendFSServesIndexAndAssets(t *testing.T) {
	root, err := rootembed.FrontendPublicFS()
	if err != nil {
		t.Fatal(err)
	}
	handler := http.FileServer(http.FS(root))
	for _, path := range []string{"/", "/app.js", "/style.css"} {
		req := httptest.NewRequest(http.MethodGet, path, nil)
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)
		if rec.Code != http.StatusOK {
			t.Fatalf("%s status=%d body=%s", path, rec.Code, rec.Body.String())
		}
		if len(rec.Body.Bytes()) == 0 {
			t.Fatalf("%s empty body", path)
		}
	}
}

func TestFrontendFSIndexContainsAppScript(t *testing.T) {
	root, err := rootembed.FrontendPublicFS()
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()
	http.FileServer(http.FS(root)).ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d", rec.Code)
	}
	body := string(rec.Body.Bytes())
	if len(body) < 100 {
		t.Fatalf("index too short: %q", body[:min(len(body), 80)])
	}
}

func TestFrontendFSAppJSReadable(t *testing.T) {
	root, err := rootembed.FrontendPublicFS()
	if err != nil {
		t.Fatal(err)
	}
	f, err := root.Open("app.js")
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	buf, err := io.ReadAll(f)
	if err != nil {
		t.Fatal(err)
	}
	if len(buf) < 1000 {
		t.Fatalf("app.js too short: %d bytes", len(buf))
	}
}
