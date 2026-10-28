from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8000
MAX_BODY_BYTES = 64 * 1024
MAX_TEXT_LENGTH = 5000
# Endpoint-i kryesor i përkthimit; mund të zëvendësohet me env var.
GOOGLE_TRANSLATE_ENDPOINT = os.environ.get(
    'LINGUA_TRANSLATE_API',
    'https://translate.googleapis.com/translate_a/single',
)
MYMEMORY_TRANSLATE_ENDPOINT = 'https://api.mymemory.translated.net/get'

LANGUAGE_NAMES = {
    'auto': 'Auto-detect',
    'sq': 'Shqip',
    'en': 'English',
    'de': 'Deutsch',
    'fr': 'Français',
    'it': 'Italiano',
    'es': 'Español',
    'tr': 'Türkçe',
    'sr': 'Srpski',
    'el': 'Ελληνικά',
}


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Shërben skedarët statikë nga folderi i projektit.
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        # Lejon kërkesa nga origjina të ndryshme, përfshirë Live Server.
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_OPTIONS(self):
        # Përgjigje për preflight CORS.
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self):
        # Route i vetëm API për përkthim.
        if self.path != '/api/translate':
            self.send_error(HTTPStatus.NOT_FOUND, 'Not found')
            return

        try:
            content_length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            self._send_json({'ok': False, 'error': 'Invalid Content-Length.'}, HTTPStatus.BAD_REQUEST)
            return
        if content_length <= 0:
            self._send_json({'ok': False, 'error': 'Request body is required.'}, HTTPStatus.BAD_REQUEST)
            return
        if content_length > MAX_BODY_BYTES:
            self._send_json({'ok': False, 'error': 'Request body is too large.'}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json({'ok': False, 'error': 'Invalid JSON payload.'}, HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(payload, dict):
            self._send_json({'ok': False, 'error': 'JSON body must be an object.'}, HTTPStatus.BAD_REQUEST)
            return

        text_value = payload.get('text', '')
        source = payload.get('source', 'auto')
        target = payload.get('target', 'en')
        if not all(isinstance(value, str) for value in (text_value, source, target)):
            self._send_json({'ok': False, 'error': 'Text and language codes must be strings.'}, HTTPStatus.BAD_REQUEST)
            return

        text = text_value.strip()
        source = source.strip().lower()
        target = target.strip().lower()

        if not text:
            self._send_json({'ok': False, 'error': 'Text is required.'}, HTTPStatus.BAD_REQUEST)
            return
        if len(text) > MAX_TEXT_LENGTH:
            self._send_json(
                {'ok': False, 'error': f'Text cannot exceed {MAX_TEXT_LENGTH} characters.'},
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
            return
        supported_languages = set(LANGUAGE_NAMES) - {'auto'}
        if source != 'auto' and source not in supported_languages:
            self._send_json({'ok': False, 'error': 'Unsupported source language.'}, HTTPStatus.BAD_REQUEST)
            return
        if target not in supported_languages:
            self._send_json({'ok': False, 'error': 'Unsupported target language.'}, HTTPStatus.BAD_REQUEST)
            return
        if source == target:
            self._send_json({'ok': False, 'error': 'Source and target languages must differ.'}, HTTPStatus.BAD_REQUEST)
            return

        try:
            response_data = translate_text(text=text, source=source, target=target)
        except urllib.error.HTTPError as error:
            self._send_json(
                {'ok': False, 'error': f'Translation service error ({error.code}). Try again later.'},
                HTTPStatus.BAD_GATEWAY,
            )
            return
        except Exception:  # noqa: BLE001
            self._send_json({'ok': False, 'error': 'Translation service is unavailable right now.'}, HTTPStatus.BAD_GATEWAY)
            return

        self._send_json({'ok': True, **response_data}, HTTPStatus.OK)

    def log_message(self, format, *args):  # noqa: A003
        return

    def _send_json(self, data, status):
        encoded = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def translate_text(text: str, source: str, target: str) -> dict[str, str | None]:
    # Provo së pari Google Translate, pastaj MyMemory si rezervë.
    response_payload = None
    detected_language_code = None

    for provider_name, provider in (
        ('google', _translate_with_google),
        ('mymemory', _translate_with_mymemory),
    ):
        try:
            response_payload = provider(text=text, source=source, target=target)
            break
        except Exception:  # noqa: BLE001
            continue

    if response_payload is None:
        raise RuntimeError('Translation service is unavailable right now.')

    translated_text = response_payload['translated_text']
    if not translated_text:
        raise RuntimeError('Translation service returned an empty result.')
    detected_language_code = response_payload.get('detected_language')

    return {
        'translated_text': translated_text,
        'detected_language': detected_language_code or (source if source != 'auto' else None),
        'detected_language_name': LANGUAGE_NAMES.get(detected_language_code, detected_language_code) if detected_language_code else None,
        'source_name': LANGUAGE_NAMES.get(source, source),
        'target_name': LANGUAGE_NAMES.get(target, target),
    }


def _translate_with_google(text: str, source: str, target: str) -> dict[str, str]:
    # Ndërton kërkesën për Google Translate dhe kthen tekstin e përkthyer.
    query_string = urllib.parse.urlencode(
        {
            'client': 'gtx',
            'sl': source,
            'tl': target,
            'dt': 't',
            'q': text,
        }
    )
    request_url = f'{GOOGLE_TRANSLATE_ENDPOINT}?{query_string}'
    request = urllib.request.Request(request_url, method='GET')

    with urllib.request.urlopen(request, timeout=30) as response:
        response_payload = json.loads(response.read().decode('utf-8'))

    translated_text = ''.join(part[0] for part in response_payload[0] if part and part[0])
    detected_language = (response_payload[2] or source) if len(response_payload) > 2 else source

    return {
        'translated_text': translated_text,
        'detected_language': detected_language,
    }


def _translate_with_mymemory(text: str, source: str, target: str) -> dict[str, str]:
    # Fallback alternativ në rast se endpoint-i kryesor dështon.
    query_string = urllib.parse.urlencode(
        {
            'q': text,
            'langpair': f'{"" if source == "auto" else source}|{target}',
        }
    )
    request_url = f'{MYMEMORY_TRANSLATE_ENDPOINT}?{query_string}'
    request = urllib.request.Request(request_url, method='GET')

    with urllib.request.urlopen(request, timeout=30) as response:
        response_payload = json.loads(response.read().decode('utf-8'))

    translated_text = response_payload.get('responseData', {}).get('translatedText', '')
    # MyMemory does not provide a reliable detected-language field for auto mode.
    detected_language = None

    return {
        'translated_text': translated_text,
        'detected_language': detected_language,
    }


def main() -> None:
    # Starton serverin lokal që shërben frontend-in dhe API-n.
    parser = argparse.ArgumentParser(description='Run the ERER Translate AI web app.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f'ERER Translate AI running at http://{args.host}:{args.port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
