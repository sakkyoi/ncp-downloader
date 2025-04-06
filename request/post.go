package request

import (
	"encoding/json"
	"errors"
	"github.com/charmbracelet/log"
	"io"
	"net/http"
)

// Post sends a POST request to the specified URL with the provided headers and body.
func Post(url string, header http.Header, body io.Reader) (io.ReadCloser, error) {
	req, err := http.NewRequest(http.MethodPost, url, body)
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

// PostJSON sends a POST request to the specified URL with the provided headers and body, and decodes the JSON response into the provided variable.
func PostJSON(url string, header http.Header, body io.Reader, v any) error {
	res, err := Post(url, header, body)
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
