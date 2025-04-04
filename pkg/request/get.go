package request

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
)

// Get sends a GET request to the specified URL with the provided headers.
func Get(url string, header http.Header) (io.ReadCloser, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}

	req.Header = header

	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}

	if res.StatusCode != http.StatusOK {
		return nil, errors.New(res.Status)
	}

	return res.Body, nil
}

// GetJSON sends a GET request to the specified URL with the provided headers and decodes the JSON response into a map.
func GetJSON(url string, header http.Header, v any) error {
	res, err := Get(url, header)
	if err != nil {
		return err
	}

	decoder := json.NewDecoder(res)
	err = decoder.Decode(v)
	if err != nil {
		return err
	}

	return nil
}
