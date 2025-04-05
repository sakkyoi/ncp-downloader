package util

import (
	"net/url"
	"strings"
)

type QueryParser struct {
	Query       string
	Scheme      string
	Host        string
	Path        string
	UserName    string
	ContentCode string // if query is a video
}

func NewQueryParser(query string) *QueryParser {
	u, err := url.Parse(query)
	if err != nil {
		panic(err)
	}

	path := strings.Split(strings.Trim(u.Path, "/"), "/")

	var userName, contentCode string
	userName = path[0] // the first part of the path must be the username

	if len(path) > 1 {
		contentCode = path[len(path)-1] // the last part of the path must be the content code
	}

	return &QueryParser{
		Query:       query,
		Scheme:      u.Scheme,
		Host:        u.Host,
		Path:        u.Path,
		UserName:    userName,
		ContentCode: contentCode,
	}
}
