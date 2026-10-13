# YouVersion Verse of the Day for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/franklinis/ha-youversion-votd/actions/workflows/validate.yml/badge.svg)](https://github.com/franklinis/ha-youversion-votd/actions/workflows/validate.yml)

A Home Assistant integration that shows the [YouVersion](https://www.bible.com/verse-of-the-day) Verse of the Day in the Bible version you choose. Put it on a dashboard, read it aloud with TTS, or send it to your phone each morning.

It uses the official [YouVersion Platform API](https://developers.youversion.com), not page scraping.

> This is a community project. It is not affiliated with or endorsed by YouVersion or Life.Church.

## What you get

One sensor per Bible version you add, for example `sensor.youversion_bsb_verse_of_the_day`:

| | Example |
|---|---|
| **State** | `Philippians 4:6-7` |
| `text` | `Be anxious for nothing, but in everything, by prayer and petition…` |
| `reference` | `Philippians 4:6-7` |
| `version` | `BSB` |
| `version_name` | `Berean Standard Bible` |
| `copyright` | The publisher's copyright notice for the version |
| `url` | `https://www.bible.com/bible/3034/PHP.4.6-7` |
| `passage_id` | `PHP.4.6-7` (USFM) |
| `bible_id`, `day_of_year`, `date` | `3034`, `286`, `2026-10-13` |

The verse text is an attribute, not the state, because Home Assistant limits states to 255 characters and some verses are longer.

## Before you install: get a free app key

1. Sign in at [platform.youversion.com](https://platform.youversion.com) and create an app.
2. Copy its **app key**.

Which Bible versions you can choose depends on the licenses attached to your app. The license-free Berean Standard Bible (BSB), which YouVersion's own SDKs use by default, is preselected when your key can read it.

## Installation

### HACS (recommended)

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/franklinis/ha-youversion-votd` with type **Integration**.
3. Search for **YouVersion Verse of the Day**, download it, and restart Home Assistant.

### Manual

Copy `custom_components/youversion_votd` into your Home Assistant `config/custom_components/` folder and restart.

## Setup

1. Go to **Settings → Devices & services → Add integration** and choose **YouVersion Verse of the Day**.
2. Paste your app key. The language defaults to your Home Assistant language; it only filters the list of Bible versions.
3. Pick a Bible version.

Add the integration again to follow more than one version.

## Examples

### Dashboard card

```yaml
type: markdown
content: |
  {% set v = 'sensor.youversion_bsb_verse_of_the_day' %}
  ## {{ states(v) }} <small>{{ state_attr(v, 'version') }}</small>

  {{ state_attr(v, 'text') }}

  <sub>{{ state_attr(v, 'copyright') }} · [Read on Bible.com]({{ state_attr(v, 'url') }})</sub>
```

### Morning notification

```yaml
alias: Verse of the day
triggers:
  - trigger: time
    at: "07:00:00"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "{{ states('sensor.youversion_bsb_verse_of_the_day') }}"
      message: "{{ state_attr('sensor.youversion_bsb_verse_of_the_day', 'text') }}"
```

### Read it aloud

```yaml
action: tts.speak
target:
  entity_id: tts.home_assistant_cloud
data:
  media_player_entity_id: media_player.kitchen
  message: >-
    {{ states('sensor.youversion_bsb_verse_of_the_day') }}.
    {{ state_attr('sensor.youversion_bsb_verse_of_the_day', 'text') }}
```

## How it works

- The verse follows YouVersion's 366-day calendar. The day is counted in your Home Assistant time zone, so the verse changes at your local midnight.
- Each day the integration makes two API calls: one for the day's passage and one for its text. Version details are fetched once at startup. If a call fails it retries hourly, and the sensor is unavailable rather than showing yesterday's verse.
- Your app key is sent only to `api.youversion.com`, and it is redacted from diagnostics.
- If YouVersion rejects the key, Home Assistant asks you for a new one.

## Attribution

Scripture text is copyrighted by each version's publisher. The sensor's `copyright` attribute and Home Assistant's attribution field carry the publisher's notice; please show it wherever you display the text, as the examples above do.

## Development

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt ruff
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## License

The code is [MIT licensed](LICENSE). Bible text belongs to its publishers.
