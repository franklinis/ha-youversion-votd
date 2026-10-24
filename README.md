# Bible Verse of the Day for Home Assistant

[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://hacs.xyz)
[![Validate](https://github.com/franklinis/ha-youversion-votd/actions/workflows/validate.yml/badge.svg)](https://github.com/franklinis/ha-youversion-votd/actions/workflows/validate.yml)

A Home Assistant integration that shows a Bible verse of the day **in the language and Bible translation you choose**. Put it on a dashboard, read it aloud with TTS, or send it to your phone each morning.

**No account or key needed.**
- **The day's verse** is picked by [DailyVerses.net](https://dailyverses.net) and read through its official website widget.
- **The text** comes from the [Free Use Bible API](https://bible.helloao.org). It offers about 1,250 public-domain and openly licensed translations in about 1,000 languages: for example the Berean Standard Bible, the World English Bible, Lutherbibel 1912, Reina-Valera, Louis Segond, and the Indian Revised Version in Tamil, Hindi, Malayalam, Telugu and Kannada.

> This is a community project, not affiliated with DailyVerses.net or the Free Use Bible API. Versions up to 0.1.x used YouVersion and needed an app key; the repository and domain keep that original name so existing installs keep working.

## What you get

One sensor per translation you add, for example `sensor.bible_bsb_verse_of_the_day`:

| | Example |
|---|---|
| **State** | `Isaiah 25:1` (in the translation's language, e.g. `Jesaja 25,1`, `ஏசாயா 25:1`) |
| `text` | `O LORD, You are my God! I will exalt You; I will praise Your name…` |
| `reference_en` | `Isaiah 25:1` |
| `passage_id` | `ISA.25.1` (USFM) |
| `translation`, `translation_name` | `BSB`, `Berean Standard Bible` |
| `language` | `eng` (ISO 639-3) |
| `license` | Link to the translation's license |
| `fallback` | `true` if the chosen translation lacks the verse and the BSB is shown instead |
| `date`, `url` | `2026-10-24`, the verse on DailyVerses.net |

The verse text is an attribute, not the state, because Home Assistant limits states to 255 characters and some verses are longer.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=franklinis&repository=ha-youversion-votd&category=integration)

Search HACS for **Bible Verse of the Day** (or click the button above), select **Download**, then restart Home Assistant.

### Manual

Copy `custom_components/youversion_votd` into your Home Assistant `config/custom_components/` folder and restart.

## Setup

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=youversion_votd)

1. Click the button above, or go to **Settings → Devices & services → Add integration** and choose **Bible Verse of the Day**.
2. Choose a language. It starts on your Home Assistant language.
3. Choose a translation. Complete Bibles are listed first.

To change the language or translation later, open the integration and choose **Reconfigure**. Add the integration again to follow several translations at once, for example Tamil and English.

## Examples

### Dashboard card

```yaml
type: markdown
content: |
  {% set v = 'sensor.bible_bsb_verse_of_the_day' %}
  ## {{ states(v) }} <small>{{ state_attr(v, 'translation') }}</small>

  {{ state_attr(v, 'text') }}

  <sub>{{ state_attr(v, 'translation_name') }} · Verse selection: [DailyVerses.net]({{ state_attr(v, 'url') }})</sub>
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
      title: "{{ states('sensor.bible_bsb_verse_of_the_day') }}"
      message: "{{ state_attr('sensor.bible_bsb_verse_of_the_day', 'text') }}"
```

### Read it aloud

```yaml
action: tts.speak
target:
  entity_id: tts.home_assistant_cloud
data:
  media_player_entity_id: media_player.kitchen
  message: >-
    {{ states('sensor.bible_bsb_verse_of_the_day') }}.
    {{ state_attr('sensor.bible_bsb_verse_of_the_day', 'text') }}
```

## How it works

- **When it checks:** once a day, just after your local midnight. DailyVerses.net follows European time, so if it hasn't moved to the new day yet, the integration asks again hourly until it does.
- **What it fetches:** the day's reference (a few hundred bytes) and, when it changes, one chapter of your translation. The list of book names is fetched once at startup; the full list of translations is only fetched while you're choosing one.
- **Verse numbering:** all translations use the same numbering, so the reference from DailyVerses.net works with every translation.
- **Missing verses:** if a translation doesn't include the day's book (for example a New Testament only translation), the verse is shown in the Berean Standard Bible and `fallback` is `true`.
- **Errors:** if a request fails, the integration retries hourly. On a new day the sensor shows as unavailable rather than keeping yesterday's verse.

## Upgrading from 0.1.x (YouVersion)

Existing entries move over automatically:
- **The app key** is removed.
- **The translation** becomes the preferred free one in your old language, falling back to the BSB.
- **The sensor** keeps its entity ID.

Use **Reconfigure** to pick a different translation.

## Attribution

Show the translation's name wherever you display the text, and credit DailyVerses.net for the selection, as the dashboard example does. Each translation's license is linked in the `license` attribute; most are public domain, some are Creative Commons with attribution.

## Development

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt ruff
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## License

The code is [MIT licensed](LICENSE). Bible texts belong to their translators and are used under their licenses.
