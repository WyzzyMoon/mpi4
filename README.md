# Mπ4 Media Player

<img width="300" height="300" alt="splash" src="https://github.com/user-attachments/assets/e94950a3-2bb2-474b-bc61-dbf8e151a69b" />


## Mediaplayer for Raspberry Pi

**Mπ4** is a simple, very configurable media player for Raspberry Pi (3b+ and up). Designed for easy-to-use video playback in art installation. Heavily inspired by [MP4MUSEUM](https://www.mp4museum.org) by Julius Schmiedel.

---

## Changelog

| Date     | Version | Changes                            |
| -------- | ------- | ---------------------------------- |
| 28/09/26 | v1beta3 | fixed multiple sync bugs           |
| 06/07/26 | v1beta2 | fixed composite output on Pi 4 & 5 |
| 03/07/26 | v1beta  | initial release                    |

**SHA256**

```text
c2c687fd7aca4f00765bad4822e57ccb6797d02de2509c487b7d65de4bf14b03
```

**MD5**

```text
8324d32b20e6bade1ac8d57d71b0c645
```

> Please note, this is in beta. There might still be some bugs. If you find any, please [get in touch!](mailto\:info@wikkeandeweg.nl)

The images can be written to a microSD card (8GB +) with the [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

---

## Features

- Media playback form USB.
- Hot-swap USB media.
- Custom settings via settings file.
- Seamless looping playback of Video, Audio and Images.
- Synced playback with multiple players.
- HDMI or Composite video output.
- HDMI or Headphone audio output.
- Automatic resolution scaling.
- Support for external trigger buttons via GPIO.
- Easy Video Wall functionality.

### Supported Media Types

| Media | Formats                                    |
| ----- | ------------------------------------------ |
| Video | `.mp4` `.mkv` `.avi` `.mov` `.m4v` `.webm` |
| Image | `.jpg` `.jpeg` `.png` `.bmp` `.webp`       |
| Audio | `.mp3` `.wav`                              |

---

## Customize

| Setting                      | Options                                    |
| ---------------------------- | ------------------------------------------ |
| **Player Mode**              | Standalone \| Sync Leader \| Sync Follower |
| **Audio Output**             | Headphones \| HDMI                         |
| **Image Hold Time**          | Amount of seconds for image slide shows    |
| **Video Rotation**           | 90, 180, 270 degrees                       |
| **Autoplay**                 | Auto start video or wait for button press  |
| **GPIO Button Assignments**  | Attach buttons to GPIO pins                |
| **Video Wall Configuration** |                                            |
| **Advanced Sync Settings**   |                                            |

All settings can be customized by placing a file called `settings.mpi4` on the same usb drive as the media. This file can be generated in the [Mπ4 Settings Generator](https://www.mpi4.org/settings.html).

---

## Hardware support

Mπ4 is fully supported on:

| Raspberry Pi     | Support         |
| ---------------- | --------------- |
| Raspberry Pi 5   | Fully supported |
| Raspberry Pi 4   | Fully supported |
| Raspberry Pi 3b+ | Fully supported |

### Older devices

| Raspberry Pi               | Support                                                                                                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Raspberry Pi 3b (non plus) | Will only work without full hardware acceleration which makes it only suitable when the media matches the native resolution of the display and no video wall or rotation is applied. |
| Raspberry Pi 1 and 2       | **Not supported** by this software.                                                                                                                                                  |

Looking for a great alternative? [MP4MUSEUM](https://www.mp4museum.org) fully supports Raspberry Pi 4 and below with hardware accelerated video.

---

## Licenses & Credits

| Component         | Details                                                             |
| ----------------- | ------------------------------------------------------------------- |
| Base              | [Raspberry Pi OS 13 (Trixie), 64-bit](https://www.raspberrypi.com/) |
| Media Playback    | [mpv](https://mpv.io/) v0.40.0-3+deb13u1, licensed GPLv2+           |
| GPIO Handling     | [gpiozero](https://gpiozero.readthedocs.io/), licensed BSD 3-Clause |
| USB Auto-mounting | [USBmount](https://github.com/rbrito/usbmount) by Rogério Brito     |
| Inspiration       | [MP4MUSEUM](https://www.mp4museum.org) by Julius Schmiedel.         |

Mπ4 is built on top of, and distributes, the above open-source projects unmodified. Full source for each is available at the links above.

Mπ4 is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License, version 3, as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

A copy of the GNU General Public License, version 3, is included with this distribution, and can also be found at [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html).

---

**Mπ4 is created by [Wikke Andeweg](https://www.wikkeandeweg.nl/). Feel free to reach out with feedback or requests by sending me an email at [info@wikkeandeweg.nl](mailto\:info@wikkeandeweg.nl).**
