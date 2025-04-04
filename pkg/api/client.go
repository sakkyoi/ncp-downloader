package api

import (
	"fmt"
	"github.com/sakkyoi/ncp-downloader/pkg/request"
	"log"
	"net/http"
	"strconv"
)

type Client struct {
	Header    http.Header
	Endpoints *Endpoints
}

func NewClient(siteBase string, userName string) *Client {
	endpoints := NewEndpoints(fmt.Sprintf("https://%s", siteBase))

	// initialize header
	header := http.Header{
		"Origin":        {siteBase},
		"Fc_use_device": {"null"},
	}

	client := &Client{
		Header:    header,
		Endpoints: endpoints,
	}

	// get api settings
	apiBaseUrl, fanclubSiteId, _, err := client.getApiSettings()
	if err != nil {
		log.Panic(err)
	}

	endpoints.ApiBaseUrl = apiBaseUrl       // set api base url
	header.Add("Fc_site_id", fanclubSiteId) // set fanclub site id header

	// if fanclub site id is 1, get it again from the channel endpoint
	if fanclubSiteId == "1" {
		channel := &struct {
			Data struct {
				ContentProviders struct {
					Domain      string `json:"domain"`
					FanclubSite struct {
						Id int `json:"id"`
					} `json:"fanclub_site"`
					Id int `json:"id"`
				} `json:"content_providers"`
			} `json:"data"`
		}{}
		if err := request.GetJSON(endpoints.GetChannelUrl(userName), header, channel); err != nil {
			log.Panic(err)
		}

		header.Set("Fc_site_id", strconv.Itoa(channel.Data.ContentProviders.FanclubSite.Id)) // set fanclub site id header
	}

	return client
}

func (c *Client) getApiSettings() (string, string, string, error) {
	settings := &struct {
		ApiBaseUrl     string `json:"api_base_url"`
		FanclubGroupId string `json:"fanclub_group_id"`
		FanclubSiteId  string `json:"fanclub_site_id"`
		PlatformId     string `json:"platform_id"`
		Channel        bool   `json:"channel"`
	}{}
	if err := request.GetJSON(c.Endpoints.GetSettingsUrl(), c.Header, settings); err != nil {
		return "", "", "", err
	}

	return settings.ApiBaseUrl, settings.FanclubSiteId, settings.PlatformId, nil
}
