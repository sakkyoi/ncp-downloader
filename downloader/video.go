package downloader

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"encoding/binary"
	"errors"
	"fmt"
	"github.com/charmbracelet/log"
	"github.com/grafov/m3u8"
	"github.com/sakkyoi/ncp-downloader/api"
	"github.com/sakkyoi/ncp-downloader/config"
	"github.com/sakkyoi/ncp-downloader/request"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

type video struct {
	ContentCode string
	ApiClient   *api.Client
	Args        config.Args
	Key         *bytes.Buffer
	VideoPage   *api.VideoPage
}

func newVideo(contentCode string, apiClient *api.Client, args config.Args) *video {
	return &video{
		ContentCode: contentCode,
		ApiClient:   apiClient,
		Args:        args,
	}
}

func (v *video) start() {
	// get video page
	videoPage, err := v.ApiClient.GetVideoPage(v.ContentCode)
	if err != nil {
		log.Error(err)
		return
	}
	v.VideoPage = videoPage // save video page to video struct

	log.Debug(nil, "videoPage", videoPage)

	// get session id
	sessionId, err := v.ApiClient.GetSessionId(v.ContentCode)
	if err != nil {
		log.Error(err)
		return
	}

	log.Debug(nil, "sessionId", sessionId)

	// get master playlist
	masterPlaylist, err := v.getMasterPlaylist(videoPage.Data.VideoPage.VideoStream.AuthencatedUrl, sessionId)
	if err != nil {
		log.Error(err)
		return
	}

	log.Debug(nil, "masterPlaylist", masterPlaylist)

	// get media playlist
	mediaPlaylist, err := v.getMediaPlaylist(masterPlaylist)
	if err != nil {
		log.Error(err)
		return
	}

	log.Debug(nil, "mediaPlaylist", mediaPlaylist)

	// get key
	key, err := v.getKey(mediaPlaylist)
	if err != nil {
		log.Error(err)
		return
	}
	v.Key = key // save key to video struct

	log.Debug(nil, "key", key.Bytes())

	// download video
	sem := make(chan struct{}, v.Args.MaxThreads)
	var wg sync.WaitGroup

	for _, segment := range mediaPlaylist.GetAllSegments() {
		sem <- struct{}{} // acquire semaphore

		wg.Add(1)

		go func(segment *m3u8.MediaSegment) {
			defer wg.Done()
			defer func() { <-sem }() // release semaphore

			// download segment
			log.Debug(nil, "start", segment.SeqId, "segment", segment.URI)

			if err := v.downloadSegment(segment); err != nil {
				log.Error(err)
				return
			}

			log.Debug(nil, "end", segment.SeqId, "segment", segment.URI)
		}(segment)
	}

	wg.Wait()
}

func (*video) getMasterPlaylist(authencatedUrl string, sessionId string) (*m3u8.MasterPlaylist, error) {
	master, err := request.Get(strings.Replace(authencatedUrl, "{session_id}", sessionId, 1), http.Header{})
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := master.Close(); err != nil {
			log.Error(err)
		}
	}()

	p, listType, err := m3u8.DecodeFrom(master, true)
	if err != nil {
		return nil, err
	}
	if listType != m3u8.MASTER {
		return nil, errors.New("not a master playlist")
	}

	return p.(*m3u8.MasterPlaylist), nil
}

func (*video) getMediaPlaylist(masterPlaylist *m3u8.MasterPlaylist) (*m3u8.MediaPlaylist, error) {
	media, err := request.Get(masterPlaylist.Variants[0].URI, http.Header{})
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := media.Close(); err != nil {
			log.Error(err)
		}
	}()

	p, listType, err := m3u8.DecodeFrom(media, true)
	if err != nil {
		return nil, err
	}

	if listType != m3u8.MEDIA {
		return nil, errors.New("not a media playlist")
	}

	return p.(*m3u8.MediaPlaylist), nil
}

func (*video) getKey(mediaPlaylist *m3u8.MediaPlaylist) (*bytes.Buffer, error) {
	var buf bytes.Buffer

	key, err := request.Get(mediaPlaylist.Key.URI, http.Header{})
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := key.Close(); err != nil {
			log.Error(err)
		}
	}()

	_, err = io.Copy(&buf, key)
	if err != nil {
		return nil, err
	}

	return &buf, nil
}

func (v *video) downloadSegment(segment *m3u8.MediaSegment) error {
	data, err := request.Get(segment.URI, http.Header{})
	if err != nil {
		return err
	}
	defer func() {
		if err := data.Close(); err != nil {
			log.Error(err)
		}
	}()

	var buf bytes.Buffer
	_, err = io.Copy(&buf, data)
	if err != nil {
		return err
	}

	// decrypt segment
	err = v.decryptSegment(segment.SeqId, &buf)
	if err != nil {
		return err
	}

	// save decrypted data to file
	// TODO: title
	path := filepath.Join(v.Args.Output, fmt.Sprintf("temp_%s", v.VideoPage.Data.VideoPage.Title), fmt.Sprintf("%d.ts", segment.SeqId))

	err = os.MkdirAll(filepath.Dir(path), os.ModePerm)

	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer func() {
		if err := file.Close(); err != nil {
			log.Error(err)
		}
	}()

	if _, err = io.Copy(file, &buf); err != nil {
		return err
	}

	return nil
}

func (v *video) decryptSegment(seq uint64, data *bytes.Buffer) error {
	block, err := aes.NewCipher(v.Key.Bytes())
	if err != nil {
		return err
	}

	// make iv
	iv := make([]byte, aes.BlockSize)
	binary.BigEndian.PutUint64(iv[8:], seq)

	log.Debug(nil, "iv", iv)

	mode := cipher.NewCBCDecrypter(block, iv) // create new CBC decrypter

	// decrypt data
	mode.CryptBlocks(data.Bytes(), data.Bytes())

	// remove padding
	pad := int(data.Bytes()[len(data.Bytes())-1])
	data.Truncate(len(data.Bytes()) - pad)

	return nil
}
