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
	ChannelName string
	ContentCode string // if query is a video
}

func NewQueryParser(query string) *QueryParser {
	u, err := url.Parse(query)
	if err != nil {
		panic(err)
	}

	path := strings.Split(strings.Trim(u.Path, "/"), "/")

	var channelName, contentCode string
	channelName = path[0] // the first part of the path must be the channel name

	if len(path) > 1 {
		contentCode = path[len(path)-1] // the last part of the path must be the content code
	}

	return &QueryParser{
		Query:       query,
		Scheme:      u.Scheme,
		Host:        u.Host,
		Path:        u.Path,
		ChannelName: channelName,
		ContentCode: contentCode,
	}
}
