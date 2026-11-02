# Mπ4 Media Player

## Media player for Raspberry Pi

**Mπ4** is a simple, very configurable media player for Raspberry Pi. Designed for easy-to-use controllable video playback in art installations and live shows.

---

## Download

Version **v1-rc1** · 02/11/26

Get the images from the [releases page](https://github.com/WyzzyMoon/mpi4/releases).

| Image                | Supported on          |
| -------------------- | --------------------- |
| 64-bit (recommended) | Raspberry Pi 5, 4 & 3 |
| 32-bit               | Raspberry Pi 2        |

**Checksums**

64-bit

```text
SHA256  130f671f2362741c223f5b43470fb14733042ff3ef4a34035b65ac411ffa2455
MD5     9c48c669a99401a7a721b22c0498d34e
```

32-bit

```text
SHA256  20bc29cba35aa551ee3655ba45eabea8da01ce4cf9dd8e0bf8e8d779b05b160e
MD5     cc29c0d4b8e119f83b391f1111636f7c
```

## Changelog

| Date     | Version | Changes                                                                         |
| -------- | ------- | ------------------------------------------------------------------------------- |
| 02/11/26 | v1-rc1  | Added web and OSC control with feedback, added support for Pi 3 & Pi 2, removed video wall feature |
| 28/09/26 | v1beta3 | fixed multiple sync bugs                                                        |
| 06/07/26 | v1beta2 | fixed composite output on Pi 4 & 5                                              |
| 03/07/26 | v1beta  | initial release                                                                 |

---

## Features

- Media playback from USB
- Hot-swap USB media
- Seamless looping
- Synced playback with multiple players
- Automatic HDMI or composite video output
- HDMI or headphone audio output
- Automatic resolution scaling
- External trigger via GPIO, web interface or OSC
- Support for subtitles

### Supported Media Types

| Media | Formats                                                           |
| ----- | ----------------------------------------------------------------- |
| Video | `.mp4` `.mkv` `.avi` `.mov` `.m4v` `.webm` `.ts` `.mpeg` `.wmv` `.flv` `.3gp` |
| Image | `.jpg` `.jpeg` `.png` `.bmp` `.webp`                              |
| Audio | `.mp3` `.wav` `.flac` `.ogg` `.opus` `.m4a` `.aac`                |

---

## Customize

| Setting                     | Options                                                     |
| --------------------------- | ----------------------------------------------------------- |
| **Player Mode**             | Player \| Sync Follower                                     |
| **Audio Output**            | Headphones \| HDMI                                          |
| **GPIO Button Assignments** | Attach buttons to GPIO pins                                 |
| **Image Hold Time**         | Amount of seconds for image slide shows                     |
| **Video Rotation**          | 90, 180, 270 degrees (on Pi 4 and up)                       |
| **Autoplay**                | Auto start video or wait for a trigger                      |

These settings can be customized with a single file named `settings.mpi4` that sits alongside the media on the USB drive. This file can be generated with the [Mπ4 Settings Generator](https://www.mpi4.org/settings.html).

To set the settings for a player instead of for the media, rename the file to `default.mpi4` and place it in `/boot/firmware/`. It overrides any `settings.mpi4`, even when the media is swapped.

---

## Licenses & Credits

| Component         | Details                                                             |
| ----------------- | ------------------------------------------------------------------- |
| Base              | [Raspberry Pi OS 13 (Trixie)](https://www.raspberrypi.com/)         |
| Media Playback    | [mpv](https://mpv.io/) v0.40.0-3+deb13u1, licensed GPLv2+           |
| GPIO Handling     | [gpiozero](https://gpiozero.readthedocs.io/), licensed BSD 3-Clause |
| USB Auto-mounting | [USBmount](https://github.com/rbrito/usbmount) by Rogério Brito     |
| OSC handling      | [python-osc](https://github.com/attwad/python-osc) by attwad        |
| Inspiration       | [MP4MUSEUM](https://www.mp4museum.org) by Julius Schmiedel.         |

Mπ4 is built on top of, and distributes, the above open-source projects unmodified. Full source for each is available at the links above.

Mπ4 is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License, version 3, as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

A copy of the GNU General Public License, version 3, is included with this distribution, and can also be found at [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html).