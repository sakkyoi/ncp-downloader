package request

import (
	"encoding/json"
	"errors"
	"github.com/charmbracelet/log"
	"io"
	"net/http"
)

// Get sends a GET request to the specified URL with the provided headers.
func Get(url string, header http.Header) (io.ReadCloser, error) {
	req, err := http.NewRequest(http.MethodGet, url, nil)
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

// GetJSON sends a GET request to the specified URL with the provided headers and decodes the JSON response into the provided variable.
func GetJSON(url string, header http.Header, v any) error {
	res, err := Get(url, header)
	if err != nil {
		return err
	}
	defer func() {
		if err := res.Close(); err != nil {
			log.Error(err)
		}
	}()

	decoder := json.NewDecoder(res)
	if err = decoder.Decode(v); err != nil {
		return err
	}

	return nil
}
