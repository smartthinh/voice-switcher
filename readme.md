# Voice Switcher

## Information
- **Author**: Smart Thinh
- **Compatibility**: NVDA version 2024.1 and beyond
- **Website**: [smartthinh.netlify.app](https://smartthinh.netlify.app/en/home)
- **Facebook**: [@smartthinh](https://facebook.com/smartthinh)
- **Telegram**: [@smartthinh](https://t.me/smartthinh)
- **Telegram Channel**: [Accessible Vision Resources](https://t.me/accessiblevisionresources)

## Introduction
Voice Switcher is an add-on that helps you switch back and forth between multiple voices of different synthesizers.

## Overall Benefits of Using Voice Switcher
Instead of opening the NVDA settings menu, navigating to voice settings, and changing individual parameters (rate, pitch, synthesizer) every time you need to switch languages, Voice Switcher fully automates this process.

The biggest benefit of the add-on is saving time and optimizing the listening experience. It is extremely useful for:
- **Multilingual users**: Easily switch from Vietnamese to English, French, Japanese, etc., when reading bilingual documents.
- **Multitaskers**: Automatically use a fast, concise voice for web browsing or coding, and automatically switch to an expressive, slower voice when opening an e-book reading app.

## Key Features, Uses, and Effects
Based on its core mechanics, Voice Switcher provides the following main features:

### 1. Voice Slots
- **Feature Name**: Set/Select Synthesizer for Slot (Default shortcuts: `NVDA + Control + Shift + 1` to `0`)
- **Use**: Provides 10 "slots" numbered from 1 to 0 for you to store your current voice configurations. This configuration saves not only the voice name but also the rate, volume, pitch, and variant.
- **Effect**: Wherever you are, simply press the shortcut for the corresponding slot, and NVDA will instantly switch to the voice saved in that slot.

### 2. Smart Saving Shortcut (Save Synth)
- **Feature Name**: Save to slot / Add or Remove app voice (Default shortcut: `NVDA + Control + Shift + S`)
- **Use & Effect**: This is a smart dual-action shortcut:
  - **Single press**: Saves your current voice configuration into the slot you most recently called.
  - **Double press**: Pins (or unpins) the current voice to the application window you are currently working in.

### 3. Multiple Voices per Slot (Multi voices per slot)
- **Feature Name**: Enable multiple voices per slot
- **Use**: Instead of each shortcut holding only 1 voice, this feature allows you to repeatedly press a slot's shortcut (double press, triple press...) to call secondary voices (e.g., slot 1 has voice 1.1, 1.2, 1.3...). You can customize the limit from 1 to 10 voices per slot.
- **Effect**: Helps expand the number of voices you can save without having to remember new shortcuts. You can group voices of the same language into a single number key and double press to choose your preferred voice.

### 4. Application Specific Voices
- **Feature Name**: Enable application specific voices
- **Use**: Allows you to link a specific voice configuration to a specific application window. (For example: Assigning an English voice for the Chrome browser, and a Vietnamese voice for Microsoft Word).
- **Effect**: Works completely automatically! Every time you use `Alt + Tab` to switch to another window, NVDA will automatically recognize it and switch to the exact voice you set for that application without needing to press any extra keys.

### 5. Quick Toggle Between 2 Main Voices (Toggle Synth 1 and 2)
- **Feature Name**: Toggle between voice slot 1 and 2 (Default shortcut: Grave accent key below Esc)
- **Use**: Instantly switches back and forth between the voice saved in Slot 1 and Slot 2 with just one keystroke.
- **Effect**: Extremely useful when you are reading a text that mixes two languages or when you need to compare information between two documents. Press once to switch languages, press again to revert back.

### 6. Central Control Panel (VoiceSwitcher Settings Panel)
- **Feature Name**: VoiceSwitcher Settings (Located in NVDA's Settings menu)
- **Use**: Provides an intuitive interface that allows you to:
  - Enable/disable the application-specific voices feature.
  - Enable/disable and configure the maximum number of voices per slot key press.
  - View the list of all applications that have specific voices assigned to them.
- **Effect**: Helps users easily manage the add-on. If you accidentally assigned the wrong voice to a software, you can go here and choose "Remove" or "Remove All" to reset your settings.

## Changelog

### Version 26.2
- Added a workaround to handle all exceptions when retrieving parameters from unsupported synthesizers (like Microsoft Speech API version 5), preventing the add-on from failing when saving voices.
- Refactored source code to align with the NVDA Add-on community's coding style guidelines (tabs for indentation and camelCase naming conventions).
- Added a shortcut (`NVDA + Control + Shift + A`) to quickly toggle application-specific voices on/off.
- Added a shortcut (`NVDA + Control + Shift + P`) to quickly toggle multiple voices per slot on/off.

### Version 26.1
- Initial Release.