//go:build ignore

package main

import (
	"fmt"

	eftarkov "bm-tarkov-map-tracker/internal/maps_eftarkov.com"
	"bm-tarkov-map-tracker/internal/maps"
)

func main() {
	fmt.Println("catalogOrder", eftarkov.CatalogOrder)
	for _, id := range eftarkov.CatalogOrder {
		fmt.Println(id, "exists", eftarkov.MapExists(id))
	}
	entries, err := maps.ListFor("eftarkov", "A")
	fmt.Println("ListFor", len(entries), err)
}
