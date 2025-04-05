package util

import "net/http"

func ConcatHeader(a, b http.Header) http.Header {
	// Create a new header to store the concatenated values
	concatHeader := http.Header{}

	// Add all headers from the first header
	for key, values := range a {
		concatHeader[key] = values
	}

	// Add all headers from the second header, appending values if the key already exists
	for key, values := range b {
		if existingValues, ok := concatHeader[key]; ok {
			concatHeader[key] = append(existingValues, values...)
		} else {
			concatHeader[key] = values
		}
	}

	return concatHeader
}
