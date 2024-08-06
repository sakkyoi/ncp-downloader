`ncp-downloader` is a tool for network performance testing by downloading videos from a well-known online video platform. 

# Installation
Download the latest release from the [Releases](https://github.com/sakkyoi/ncp-downloader/releases/latest) page
and extract it to the directory of your choice on your local machine.

# Usage
`ncp QUERY [OUTPUT_DIR] [OPTIONS]`

QUERY is a URL of video or channel.

```
-r RESOLUTION, --resolution RESOLUTION      Target resolution. Defaults to highest resolution.
-R, --resume                                Resume download.
-t, --transcode                             Transcode video.
--ffmpeg FFMPEG                             Path to ffmpeg. Defaults to ffmpeg in PATH.
--vcodec VCODEC                             Video codec for transcoding.
--acodec ACODEC                             Audio codec for transcoding.
--ffmpeg-options FFMPEG_OPTIONS             Additional ffmpeg options. (e.g. --ffmpeg-options "-acodec copy -vcodec copy")
--thread THREAD                             Number of threads for downloading. Defaults to 1. (highly not recommended)
--select-manually                           Select video manually. This option only works with channel.
--username USERNAME                         Username for login.
--password PASSWORD                         Password for login.
--debug                                     Enable debug mode.
--help                                      Show help message.
```

**If login credentials are provided, a session token will be generated and saved locally.
DO NOT SHARE THE TOKEN WITH ANYONE.**<br>
Sometimes this tool may not function properly, delete temp files and folder to make it re-download the video.<br>
(Feel free to modify the .json file if you understand what you are doing.)

## `Using this tool may lead to account suspension or ban. Use it at your own discretion.`

# Disclaimer
Please do use this tool responsibly and respect the rights of the content creators.<br>
You should **ONLY** use this tool for network performance testing under any circumstances.<br>
Data downloaded using this tool should be for personal use only. Obtain permission from the original creator before use.

# License
This project is licensed under the LGPLv3 License - see the [LICENSE](LICENSE) file for details.