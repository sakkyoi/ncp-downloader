`ncp-downloader` is a tool for network performance testing by downloading videos from a well-known online video platform. 

<p align="left">
  <a href="#installation">Installation</a>
   • 
  <a href="#usage">Usage</a>
   • 
  <a href="#disclaimer">Disclaimer</a>
   • 
  <a href="#license">License</a>
</p>

# Installation
Download the latest release from the [Releases](https://github.com/sakkyoi/ncp-downloader/releases/latest) page
and extract it to the directory of your choice on your local machine.

# Usage
`ncp QUERY [OUTPUT_DIR] [OPTIONS]`

`QUERY`: URL of the video or channel.

```
-r RESOLUTION, --resolution RESOLUTION      Target resolution. Defaults to highest resolution available.
-R, --resume                                Resume download.
-t, --transcode                             Transcode downloaded videos.
--ffmpeg /PATH/TO/FFMPEG                    Path to ffmpeg. Defaults to ffmpeg stored in PATH.
--vcodec VCODEC                             Video codec for transcoding.
--acodec ACODEC                             Audio codec for transcoding.
--ffmpeg-options FFMPEG_OPTIONS             Additional ffmpeg options. (e.g. --ffmpeg-options "-acodec copy -vcodec copy")
--thread THREAD                             Number of threads for downloading. Defaults to 1. (**NOT RECOMMENDED**)
--select-manually                           Select videos manually. This option only works when downloading the whole channel.
--username USERNAME                         Username for login.
--password PASSWORD                         Password for login.
--debug                                     Enable debug mode (displays debug messages).
--help                                      Show help menu.
```

**If login credentials are provided, a session token will be generated and saved locally.
DO NOT SHARE THE TOKEN WITH ANYONE.**<br>
Sometimes this tool may not function properly, delete temp files and folder to make it re-download the video.<br>
(Feel free to modify the .json file if you understand what you are doing.)

## --select-manually
When downloading the whole channel, you can use this option to manually select the videos to be downloaded.
- `Arrow Up`/`Arrow Down`, `Arrow Left`/`Arrow Right`: Navigate
- `Space`: Select / Deselect
- `Enter`: Start download
- `Ctrl + A`: Select all
- `Ctrl + R`: Deselct all
- `Ctrl + W`: Use filter

The filter supports either with noarmal keyword-filtering or lambda expression (**Case-Sensitive**). <br>
Videos will be selected if they match the conditions.
- `/only <keyword>`: Select videos that contain the keyword only.
- `/add <keyword>`: Add the videos that contain the keyword to selection.
- `/remove <keyword>`: Remove the videos that contains the keyword from selection.
- `/lambda <lambda expression>`: Use lambda expression to filter the videos.

The syntax of the lambda expression does not need to include the `lambda x:` part, and should return a boolean value. <br>
The following is an example of a lambda expression that selects the video with 
- title containing "ASMR"; 
- length of title is greater than 30; 
- index is greater than 10; 
- and the content code contains letter "R".

`/lambda "ASMR" in x.title and len(x.title) > 30 and x.index > 10 and "R" in x.content_code`

The x object has the following attributes:
- `title`: Title of the video.
- `index`: Index of the video.
- `content_code`: Content code of the video.

**NOTE: lambda expression is case-sensitive. You can use `.lower()` to make it all lowercase.**<br>
**Python built-in functions and variables are supported in the lambda expression.**

# Disclaimer

**`Using this tool may lead to account suspension or ban. Use it at your own discretion.`**

Please do use this tool responsibly and respect the rights of the content creators.<br>
You should **ONLY** use this tool for network performance testing under any circumstances.<br>
Data downloaded using this tool should be for personal use only. Obtain permission from the original creator before use.

# License
This project is licensed under the LGPLv3 License - see the [LICENSE](LICENSE) file for details.