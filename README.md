# AMC Seats Chrome Extension

A Chrome extension component of a larger system designed to monitor seat availability for AMC theater showings and notify users when their desired seat becomes available.

## Note

This repository contains only the Chrome extension portion of the AMC Seat Checker system. The complete notification system requires additional components that are maintained in separate repositories:

- [Backend FastAPI server for handling notifications](https://github.com/rzh4321/amc-seats-backend)
- [Automated web scraper for seat monitoring](.)

## Features

- Check real-time seat availability for AMC theater showings
- User-friendly popup interface
- Support for all standard AMC theater seating formats (A1-Z50)
- Integration capabilities with notification backend

## Project Structure

```txt
amc-seat-checker/
├── manifest.json        # Extension configuration
├── popup.html          # Extension popup interface
├── popup.js            # Popup functionality
└── content.js          # Content script for seat checking
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

- Built using Chrome Extension Manifest V3
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
