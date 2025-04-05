package api

import "fmt"

// Endpoints contains the API endpoints
type Endpoints struct {
	SiteBaseUrl  string
	ApiBaseUrl   string
	Settings     string
	Channel      string
	ChannelInfo  string
	VideoPages   string
	PublicStatus string
	SessionId    string
	VideoList    string
}

func NewEndpoints(baseUrl string) *Endpoints {
	return &Endpoints{
		SiteBaseUrl:  baseUrl,
		Settings:     "%s/site/settings.json",
		Channel:      "%s/content_providers/channel_domain?current_site_domain=%s",
		ChannelInfo:  "%s/fanclub_sites/%d/page_base_info",
		VideoPages:   "%s/video_pages/%s",
		PublicStatus: "%s/video_pages/%s/public_status",
		SessionId:    "%s/video_pages/%s/session_ids",
		VideoList:    "%s/fanclub_sites/%d/video_pages?vod_type=%d&page=%d&per_page=%d&sort=%s",
	}
}

func (e *Endpoints) checkApiBaseUrl() {
	if e.ApiBaseUrl == "" {
		panic("ApiBaseUrl is not set")
	}
}

func (e *Endpoints) GetSettingsUrl() string {
	return fmt.Sprintf(e.Settings, e.SiteBaseUrl)
}

func (e *Endpoints) GetChannelUrl(userName string) string {
	e.checkApiBaseUrl()

	return fmt.Sprintf(e.Channel, e.ApiBaseUrl, fmt.Sprintf("%s/%s", e.SiteBaseUrl, userName))
}

func (e *Endpoints) GetChannelInfoUrl(channelId int) string {
	e.checkApiBaseUrl()

	return fmt.Sprintf(e.ChannelInfo, e.ApiBaseUrl, channelId)
}

func (e *Endpoints) GetVideoPagesUrl(contentCode string) string {
	e.checkApiBaseUrl()

	return fmt.Sprintf(e.VideoPages, e.ApiBaseUrl, contentCode)
}

func (e *Endpoints) GetPublicStatusUrl(contentCode string) string {
	e.checkApiBaseUrl()

	return fmt.Sprintf(e.PublicStatus, e.ApiBaseUrl, contentCode)
}

func (e *Endpoints) GetSessionIdUrl(contentCode string) string {
	e.checkApiBaseUrl()

	return fmt.Sprintf(e.SessionId, e.ApiBaseUrl, contentCode)
}

func (e *Endpoints) GetVideoListUrl(channelId int, vodType int, page int, perPage int, sort string) string {
	e.checkApiBaseUrl()

	return fmt.Sprintf(e.VideoList, e.ApiBaseUrl, channelId, vodType, page, perPage, sort)
}
