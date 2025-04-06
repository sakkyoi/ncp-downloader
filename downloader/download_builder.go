package downloader

import (
	"github.com/charmbracelet/log"
	"github.com/sakkyoi/ncp-downloader/api"
	"github.com/sakkyoi/ncp-downloader/config"
	"github.com/sakkyoi/ncp-downloader/util"
)

type DownloadBuilder struct {
	Query *util.QueryParser
	Args  config.Args
}

func BuildDownloader(query *util.QueryParser, args config.Args) *DownloadBuilder {
	return &DownloadBuilder{
		Query: query,
		Args:  args,
	}
}

func (du *DownloadBuilder) Start() {
	apiClient, err := api.NewClient(du.Query)
	if err != nil {
		log.Fatal(err)
	}

	if du.Query.ContentCode != "" {
		// download video
		newVideo(du.Query.ContentCode, apiClient, du.Args).start()
	} else {
		// not implemented
		log.Fatal("not implemented")
	}
}
