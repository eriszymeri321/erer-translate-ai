# ERER Translate AI

ERER Translate AI is a lightweight web application for translating text through a simple, responsive interface. Users can enter text, choose a source and target language, and view or copy the translation.

## Features

- Translate between Albanian, English, German, French, Italian, Spanish, Turkish, Serbian, and Greek
- Automatically detect the source language when supported by the translation provider
- Swap source and target languages
- Count input characters, clear the text, and copy the translation
- Responsive layout for desktop and mobile screens
- Validate API requests and limit input to 5,000 characters

## How it works

The browser displays the interface and handles user interactions. When the user requests a translation, the JavaScript frontend sends the text and selected language codes as JSON to the Python backend at `POST /api/translate`. The backend validates the request, calls the translation service, and returns the result as JSON for the page to display.

The backend tries the public Google Translate endpoint first and MyMemory as a fallback. MyMemory does not reliably report the detected source language, so that label may be omitted when the fallback handles an auto-detect request. Both providers are external services and require an internet connection.

## Technologies

- **HTML5** for the page structure
- **CSS3** for styling, responsive layout, and visual effects
- **JavaScript (ES6+)** for interface behavior and API requests
- **Python 3.10+** for the local HTTP server and translation API
- **Python standard library** (`http.server`, `urllib`, and `json`) for serving files and making provider requests
- **Google Fonts (Inter)** for typography

No third-party Python packages are required.

## Supported languages

| Code | Language |
| --- | --- |
| `sq` | Albanian |
| `en` | English |
| `de` | German |
| `fr` | French |
| `it` | Italian |
| `es` | Spanish |
| `tr` | Turkish |
| `sr` | Serbian |
| `el` | Greek |

The source language can also be set to automatic detection (`auto`).

## Run locally

1. Install Python 3.10 or newer.
2. Clone this repository and open its folder in a terminal.
3. Start the server:

   ```bash
   python3 server.py
   ```

4. Open <http://127.0.0.1:8000> in your browser.

The server binds to `127.0.0.1` by default. When using VS Code Live Server, keep `python3 server.py` running in a separate terminal; the frontend detects the local development server and sends API calls to port 8000.

## Configuration

To use a different Google-compatible translation endpoint, set `LINGUA_TRANSLATE_API` before starting the server:

```bash
export LINGUA_TRANSLATE_API="https://your-translate-api.example/get"
python3 server.py
```

For a frontend and backend hosted on different origins, set `window.__LINGUA_API_BASE__` in a script before `app.js` loads:

```html
<script>window.__LINGUA_API_BASE__ = "https://your-api.example";</script>
<script src="app.js"></script>
```

## Project files

- `index.html` — application page and controls
- `styles.css` — visual design and responsive styles
- `app.js` — frontend behavior and API communication
- `server.py` — static file server and translation API
- `Dokumentimi_ERER_Translate_AI_20_Slide.doc` — project presentation/documentation

## Credits

Created by Eris Zymeri and Erion Mehmeti.
