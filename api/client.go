package api

import (
	"bytes"
	"errors"
	"fmt"
	"github.com/sakkyoi/ncp-downloader/request"
	"github.com/sakkyoi/ncp-downloader/util"
	"net/http"
	"strconv"
)

type Client struct {
	Header    http.Header
	Endpoints *Endpoints
	ChannelId int       // fanclub site id
	Settings  *Settings // site settings
	Channel   *Channel  // channel settings
}

type Channel struct {
	Data struct {
		ContentProviders struct {
			Domain      string `json:"domain"`
			FanclubSite struct {
				Id int `json:"id"`
			} `json:"fanclub_site"`
			Id int `json:"id"`
		} `json:"content_providers"`
	} `json:"data"`
}

func NewClient(queryParser *util.QueryParser) (*Client, error) {
	endpoints := NewEndpoints(fmt.Sprintf("%s://%s", queryParser.Scheme, queryParser.Host))

	// initialize header
	header := http.Header{
		"Origin":        {endpoints.SiteBaseUrl},
		"Fc_use_device": {"null"},
	}

	client := &Client{
		Header:    header,
		Endpoints: endpoints,
	}

	// get api settings
	apiBaseUrl, fanclubSiteId, _, err := client.getApiSettings()
	if err != nil {
		return nil, err
	}

	endpoints.ApiBaseUrl = apiBaseUrl       // set api base url
	header.Add("Fc_site_id", fanclubSiteId) // set fanclub site id header

	// convert fanclubSiteId to int and
	channelId, err := strconv.Atoi(fanclubSiteId)
	if err != nil {
		return nil, err
	}
	client.ChannelId = channelId

	// if fanclub site id is 1, get it again from the channel endpoint
	if fanclubSiteId == "1" {
		channel := &Channel{}
		if err := request.GetJSON(endpoints.GetChannelUrl(queryParser.ChannelName), header, channel); err != nil {
			return nil, err
		}

		client.Channel = channel

		header.Set("Fc_site_id", strconv.Itoa(channel.Data.ContentProviders.FanclubSite.Id)) // set fanclub site id header
		client.ChannelId = channel.Data.ContentProviders.FanclubSite.Id
	}

	return client, nil
}

type Settings struct {
	ApiBaseUrl     string `json:"api_base_url"`
	FanclubGroupId string `json:"fanclub_group_id"`
	FanclubSiteId  string `json:"fanclub_site_id"`
	PlatformId     string `json:"platform_id"`
	Channel        bool   `json:"channel"`
}

// getApiSettings returns api base url, fanclub site id and platform id
func (c *Client) getApiSettings() (string, string, string, error) {
	settings := &Settings{}
	if err := request.GetJSON(c.Endpoints.GetSettingsUrl(), c.Header, settings); err != nil {
		return "", "", "", err
	}

	c.Settings = settings

	return settings.ApiBaseUrl, settings.FanclubSiteId, settings.PlatformId, nil
}

type ChannelInfo struct {
	Data struct {
		FanclubSite struct {
			FanclubSiteName string `json:"fanclub_site_name"` // we only need this at this moment
		} `json:"fanclub_site"`
	} `json:"data"`
}

// GetChannelInfo returns channel info including fanclub site name
func (c *Client) GetChannelInfo() (*ChannelInfo, error) {
	if c.ChannelId == 0 {
		return nil, errors.New("ChannelId not set")
	}

	channelInfo := &ChannelInfo{}
	if err := request.GetJSON(c.Endpoints.GetChannelInfoUrl(c.ChannelId), c.Header, channelInfo); err != nil {
		return nil, err
	}

	return channelInfo, nil
}

type VideoList struct {
	Data struct {
		VideoPages struct {
			List []struct {
				ContentCode string `json:"content_code"`
			} `json:"list"`
			Total int `json:"total"`
		} `json:"video_pages"`
	} `json:"data"`
}

// GetVideoList returns a list of video content codes
func (c *Client) GetVideoList() ([]string, error) {
	var contentCodeList []string

	const (
		VodType = 0
		PerPage = 12
		Sort    = "-display_date"
	)

	page := 1
	total := -1

	for len(contentCodeList) < total || total == -1 {
		videoList := &VideoList{}
		if err := request.GetJSON(c.Endpoints.GetVideoListUrl(c.ChannelId, VodType, page, PerPage, Sort), c.Header, videoList); err != nil {
			return nil, err
		}

		for _, video := range videoList.Data.VideoPages.List {
			contentCodeList = append(contentCodeList, video.ContentCode)
		}

		// check if the total number of videos has changed
		if total != -1 && total != videoList.Data.VideoPages.Total {
			return nil, errors.New("video list changed during fetching process")
		}

		total = videoList.Data.VideoPages.Total
		page++
	}

	return contentCodeList, nil
}

type SessionId struct {
	Data struct {
		SessionId string `json:"session_id"`
	} `json:"data"`
}

// GetSessionId returns session id used to get m3u8 url
func (c *Client) GetSessionId(contentCode string) (string, error) {
	header := util.ConcatHeader(c.Header, http.Header{"Content-Type": {"application/json"}}) // set content type to application/json
	body := bytes.NewBuffer([]byte("{}"))                                                    // empty json body

	sessionId := &SessionId{}
	if err := request.PostJSON(c.Endpoints.GetSessionIdUrl(contentCode), header, body, sessionId); err != nil {
		return "", err
	}

	return sessionId.Data.SessionId, nil
}

type PublicStatus struct {
	Data struct {
		VideoPage struct {
			ReleasedAt string `json:"released_at"`
		} `json:"video_page"`
	} `json:"data"`
}

// GetPublicStatus returns data including released_at, which can get release date of some videos cannot be fetched by GetVideoPage
func (c *Client) GetPublicStatus(contentCode string) (*PublicStatus, error) {
	publicStatus := &PublicStatus{}
	if err := request.GetJSON(c.Endpoints.GetPublicStatusUrl(contentCode), c.Header, publicStatus); err != nil {
		return nil, err
	}

	return publicStatus, nil
}

type VideoPage struct {
	Data struct {
		VideoPage struct {
			Title         string `json:"title"`
			ThumbnailUrl  string `json:"thumbnail_url"`
			LiveStartedAt string `json:"live_started_at"`
			ReleasedAt    string `json:"released_at"`
			VideoStream   struct {
				AuthencatedUrl string `json:"authenticated_url"`
			} `json:"video_stream"`
		} `json:"video_page"`
	} `json:"data"`
}

// GetVideoPage returns video page data including title, thumbnail url, live started at, released at and url used to get m3u8
func (c *Client) GetVideoPage(contentCode string) (*VideoPage, error) {
	videoPage := &VideoPage{}
	if err := request.GetJSON(c.Endpoints.GetVideoPagesUrl(contentCode), c.Header, videoPage); err != nil {
		return nil, err
	}

	return videoPage, nil
}
