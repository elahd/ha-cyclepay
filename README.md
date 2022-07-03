<p align="center"><img width="40%" src="https://user-images.githubusercontent.com/466460/174525294-68ada609-bc40-4784-8ae0-69306b007817.png" /></p>
<h1 align="center">CyclePay for Home Assistant</h1>
<h3 align="center">Home Assistant Integration for ESD / Hercules CyclePay Laundry Rooms</h3>
<p align="center">This is an unofficial project that is not affiliated with ESD or Hercules.</p>
<br />
<p align="center">
  <a href="https://www.codacy.com/gh/elahd/ha-cyclepay/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=elahd/ha-cyclepay&amp;utm_campaign=Badge_Grade"><img src="https://app.codacy.com/project/badge/Grade/b12010b0327a484b970042deb633f76e"/></a>
  <a href="https://results.pre-commit.ci/latest/github/elahd/ha-cyclepay/main"><img src="https://results.pre-commit.ci/badge/github/elahd/ha-cyclepay/main.svg" /></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Default-41BDF5.svg" /></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" /></a>
  <a href="https://github.com/PyCQA/pylint"><img src="https://img.shields.io/badge/linting-pylint-yellowgreen" /></a>
  <a href="https://github.com/elahd/ha-cyclepay/blob/main/LICENSE"><img alt="GitHub" src="https://img.shields.io/github/license/elahd/ha-cyclepay"></a>
  <a href="https://www.buymeacoffee.com/elahd"><img src="https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg"></a>
</p>

<hr />

## Availability

This integration can be used by anyone who lives in an apartment building and uses one of the below apps to pay for laundry cycles:

| Logo                                                                                                                           | Name              | Links                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ![esd cyclepay logo](https://user-images.githubusercontent.com/466460/174422476-2e2804e7-7b4d-4d4e-b4b0-0b15b34d2d11.png)      | ESD CyclePay      | [[iOS]](https://apps.apple.com/us/app/cyclepay-laundry-app/id904361786) [[Android]](https://play.google.com/store/apps/details?id=com.esd.laundrylink&gl=US)             |
| ![hercules cyclepay logo](https://user-images.githubusercontent.com/466460/174422481-50703225-516d-40b6-abca-a9adc3e199a3.png) | Hercules CyclePay | [[iOS]](https://apps.apple.com/us/app/hercules-cyclepay/id1520002517?uo=4) [[Android]](https://play.google.com/store/apps/details?id=com.esd.laundrylink.hercules&gl=US) |

This integration has only been tested with a facility managed by Hercules, an outsource laundry company serving the NYC metropolican area. Please open a GitHub issue to report compatibility issues with other providers.

## Intro

CyclePay for Home Assistant is a [Home Assistant](https://home-assistant.io) integration that uses ESD's CyclePay / LaundryLink system to display information about the washers and dryers in your building's laundry room in Home Assistant.

Use this integration to:

1. **Avoid disappointment:** Check whether any machines are available before you head down to your laundry room.
2. **Prepare emotionally:** If no machines are available, know how long you need to wait to clean your undies.

## Features

### CyclePay Laundry Card Balance

Shows balance on your virtual laundry card.

<img width="400px" src="https://user-images.githubusercontent.com/466460/174522354-86401d5d-c885-4bb0-a7ff-dd78e968e590.png">

### Sensors for Individual Machines

Shows status of individual washers and dryers.

<img width="400px" src="https://user-images.githubusercontent.com/466460/174522757-0b2e73bb-ba62-4f11-8f5b-51733a37ae19.png">

1. Time Remaining sensor
2. Machine Running sensor (disabled by default)

### Sensors for All Machines (by Type)

Show how many washers and dryers are available now, in 15 min, 30 min, 45 min, and 60 min. Future availability based on time remaining on currently-running machines.

<img width="400px" src="https://user-images.githubusercontent.com/466460/174523202-e2faae16-a579-44f3-82d5-c569b3560721.png">

## Installation

Install via HACS.

## Future Plans

1. Support adding funds to machines.
2. Support creating timer for selected in-use machines, probably automatically after adding funds.

## Python Library

This integration communicates with CyclePay via:
<p><a href="https://github.com/elahd/pylaundry">
<img src="https://user-images.githubusercontent.com/466460/174422077-452bdd5c-243b-4487-8bd8-07a0120284d2.png" width="200px" />
</a></p>
