# AMC SeatAlert Chrome Extension

A [Chrome extension](https://chromewebstore.google.com/detail/amc-seatalert/gcehgmpfomiadbpkllbhmckebodcjkbe) for monitoring seat availability for AMC theater showings and notify users when their desired seat becomes available.

## Note

This repository contains only the Chrome extension and automated web scraper of the AMC Seat Checker system. The backend server for processing notifications is maintained in a separate repository:

- [Backend FastAPI server for handling notifications](https://github.com/rzh4321/amc-seats-backend)

## Features

- Check real-time seat availability for AMC theater showings
- User-friendly popup interface, consistent with AMC's theme
- Support for all standard AMC theater seating formats (A1-Z50)
- Integration capabilities with notification backend

## Project Structure

```txt
amc-seat-checker/
├── manifest.json
├── popup.html
├── popup.js
└── content.js
```

## Local Development

To modify and test the extension in Chrome:

1. Clone this repository:

```bash
git clone https://github.com/rzh4321/amc-seats
```

1. Open Chrome and navigate to `chrome://extensions/`

2. Enable "Developer mode" in the top right corner

3. Click "Load unpacked" and select the extension directory

## Technical Details

- Built using Chrome Extension Manifest V3 and Selenium for web scraping
- Uses content scripts to interact with AMC's seating interface
- Implements asynchronous messaging between popup and content scripts

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this code for any purpose.

## Contact

- [GitHub](https://github.com/rzh4321)
- [Email](rzh4321@gmail.com)
