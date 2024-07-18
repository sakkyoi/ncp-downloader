ncp-downloader is a tool to do network testing by download videos from a well-known video platform. 

# Installation
download the latest release from the [releases page](https://github.com/sakkyoi/ncp-downloader/releases/latest) and extract it.

# Usage
`ncp QUERY [OUTPUT_DIR] [OPTIONS]`

QUERY is a URL of video or channel.

```
-r RESOLUTION, --resolution RESOLUTION      Target resolution. Defaults to highest resolution.
-R, --resume                                Resume download.
-e, --experimental                          Experimental download method.
-t, --transcode                             Transcode video.
--ffmpeg FFMPEG                             Path to ffmpeg. Defaults to ffmpeg in PATH.
--vcodec VCODEC                             Video codec for transcoding.
--acodec ACODEC                             Audio codec for transcoding.
--ffmpeg-options FFMPEG_OPTIONS             Additional ffmpeg options. (e.g. --ffmpeg-options "-acodec copy -vcodec copy")
--thread THREAD                             Number of threads for downloading. Defaults to 1. (highly not recommended)
--username USERNAME                         Username for login.
--password PASSWORD                         Password for login.
--debug                                     Enable debug mode.
--help                                      Show help message.
```
**If username and password are provided, a token will be generated and saved in the current directory. 
DO NOT SHARE THE TOKEN WITH ANYONE.**<br>
Sometime this tool may not work properly, you can delete temp files and folder to make it re-download the video.
(feel free to modify the json file when you know what you are doing)

## `This tool may cause account suspension or ban. Use it at your own risk.`

# Disclaimer
Please do use this tool responsibly and respect the rights of the content creators.<br>
Every data downloaded using this tool should be for personal use only and should be just for network testing purposes.

# License
This project is licensed under the LGPLv3 License - see the [LICENSE](LICENSE) file for details.