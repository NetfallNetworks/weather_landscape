"""
Web Worker for Weather Landscape

Handles all HTTP requests:
- Landing page, forecasts, guide
- Image serving from R2
- Admin dashboard and API
- Manual generation (enqueues to queue)
"""

import json
from datetime import datetime
from js import Response
from workers import WorkerEntrypoint
import os


from shared import (
    FORMAT_CONFIGS,
    DEFAULT_FORMAT,
    load_template,
    render_template,
    to_js,
    get_active_zips,
    get_formats_for_zip,
    add_format_to_zip,
    remove_format_from_zip,
    add_zip_to_active,
    get_all_zips_from_r2,
    get_formats_per_zip
)


class Default(WorkerEntrypoint):
    """
    Web Worker for Weather Landscape
    Handles all HTTP requests
    """

    async def on_fetch(self, request, env, ctx):
        """
        HTTP request handler - serves images from R2

        Routes:
        Public (allow-listed):
        - GET / - Returns HTML info page with links to all ZIPs in R2
        - GET /{zip} - Returns latest weather image for ZIP (default format)
        - GET /{zip}?{format} - Returns image in specified format

        Admin (protected under /admin/*):
        - GET /admin - Admin dashboard for managing ZIPs and formats
        - GET /admin/status - Returns generation status and metadata for all ZIPs
        - GET /admin/formats?zip={zip} - Get configured formats for a ZIP
        - POST /admin/activate?zip={zip} - Add ZIP to active regeneration list
        - POST /admin/deactivate?zip={zip} - Remove ZIP from active regeneration list
        - POST /admin/formats/add?zip={zip}&format={format} - Add format to a ZIP
        - POST /admin/formats/remove?zip={zip}&format={format} - Remove format from a ZIP
        - POST /admin/generate?zip={zip} - Manually trigger generation for a ZIP
        """
        # Debug: Check env at entry point
        print(f"on_fetch called. env type: {type(env)}, env is None: {env is None}")
        if env is not None:
            print(f"env bindings: {[attr for attr in dir(env) if not attr.startswith('_')]}")

        url = request.url
        method = request.method
        path_parts = url.split('?')[0].split('/')
        path = path_parts[-1] if len(path_parts) > 0 else ''

        # Extract query parameters
        query_params = {}
        if '?' in url:
            query_string = url.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value
                else:
                    # Handle standalone parameters like ?rgb_dark (no value)
                    query_params[param] = ''

        # Extract ZIP from path - matches /{zip} pattern
        zip_from_path = None
        for part in path_parts:
            if part and part.isdigit() and len(part) == 5:
                zip_from_path = part
                break

        # Route: Serve favicon
        if path == 'favicon.ico' or path == 'favicon.png':
            return await self._serve_favicon(env)

        # Route: Admin page
        if path == 'admin':
            return await self._serve_admin(env)

        # Route: Guide page
        if path == 'guide' and 'diagram' not in path_parts:
            return await self._serve_guide()

        # Route: Serve CSS file
        if 'assets' in path_parts and 'styles.css' in path:
            return await self._serve_css()

        # Route: Serve diagram image
        if 'assets' in path_parts and path == 'diagram.png':
            return await self._serve_diagram()

        # Route: Serve example image
        if path == 'example' and not zip_from_path:
            return await self._serve_example(env)

        # Route: Landing page (root)
        if path == '' and not zip_from_path:
            return await self._serve_landing()

        # Route: Forecasts page
        if path == 'forecasts' and not zip_from_path:
            return await self._serve_forecasts(env)

        # Route: Serve image for ZIP
        if zip_from_path and path != 'status':
            return await self._serve_image(env, zip_from_path, query_params, path_parts)

        # Route: Status endpoint
        if path == 'status' and 'admin' in path_parts:
            return await self._serve_status(env)

        # Route: POST /admin/activate
        if method == 'POST' and path == 'activate' and 'admin' in path_parts:
            return await self._handle_activate(env, query_params)

        # Route: POST /admin/deactivate
        if method == 'POST' and path == 'deactivate' and 'admin' in path_parts:
            return await self._handle_deactivate(env, query_params)

        # Route: POST /admin/formats/add
        if method == 'POST' and path == 'add' and 'formats' in path_parts and 'admin' in path_parts:
            return await self._handle_format_add(env, query_params)

        # Route: POST /admin/formats/remove
        if method == 'POST' and path == 'remove' and 'formats' in path_parts and 'admin' in path_parts:
            return await self._handle_format_remove(env, query_params)

        # Route: GET /admin/formats
        if method == 'GET' and path == 'formats' and 'admin' in path_parts:
            return await self._handle_format_get(env, query_params)

        # Route: POST /admin/generate - enqueue jobs to queue
        if method == 'POST' and path == 'generate' and 'admin' in path_parts:
            return await self._handle_generate(env, query_params)

        # Default: 404
        return Response.new(
            json.dumps({'error': 'Not found'}),
            {
                'status': 404,
                'headers': {'Content-Type': 'application/json'}
            }
        )

    async def _serve_favicon(self, env):
        """Serve favicon"""
        try:
            workers_dir = os.path.dirname(__file__)
            favicon_path = os.path.join(workers_dir, 'assets', 'favicon.png')
            with open(favicon_path, 'rb') as f:
                image_bytes = f.read()

            from js import Uint8Array
            js_array = Uint8Array.new(len(image_bytes))
            for i, byte in enumerate(image_bytes):
                js_array[i] = byte

            return Response.new(js_array, headers=to_js({
                "content-type": "image/png",
                "cache-control": "public, max-age=86400"
            }))
        except Exception as e:
            return Response.new('', {'status': 404})

    async def _serve_admin(self, env):
        """Serve admin dashboard"""
        try:
            if env is None:
                print("ERROR: env is None in _serve_admin")
                return Response.new(
                    json.dumps({'error': 'Internal error: environment not available'}),
                    {'status': 500, 'headers': {'Content-Type': 'application/json'}}
                )

            all_zips = await get_all_zips_from_r2(env)
            active_zips = await get_active_zips(env)
            zip_formats = await get_formats_per_zip(env)

            zip_configured_formats = {}
            for zip_code in all_zips:
                zip_configured_formats[zip_code] = await get_formats_for_zip(env, zip_code)

            zip_rows_html = []
            for zip_code in all_zips:
                is_active = zip_code in active_zips
                active_checked = 'checked' if is_active else ''
                configured = zip_configured_formats.get(zip_code, [DEFAULT_FORMAT])

                format_checkboxes = []
                for fmt, fmt_info in FORMAT_CONFIGS.items():
                    checked_attr = 'checked' if fmt in configured else ''
                    disabled_attr = 'disabled' if fmt == DEFAULT_FORMAT else ''
                    format_checkboxes.append(
                        f'''<label class="format-checkbox">
                            <input type="checkbox" {checked_attr} {disabled_attr}
                                onchange="toggleFormat('{zip_code}', '{fmt}', this.checked)"
                                data-zip="{zip_code}" data-format="{fmt}">
                            {fmt_info['title']}
                        </label>'''
                    )
                formats_html = '<div class="format-list">' + ''.join(format_checkboxes) + '</div>'

                available = zip_formats.get(zip_code, [])
                available_html = ', '.join(available) if available else '<em>none</em>'

                zip_rows_html.append(f'''
                    <tr data-zip="{zip_code}">
                        <td class="zip-cell">{zip_code}</td>
                        <td class="active-cell">
                            <label class="switch">
                                <input type="checkbox" {active_checked}
                                    onchange="toggleActive('{zip_code}', this.checked)">
                                <span class="slider"></span>
                            </label>
                        </td>
                        <td class="formats-cell">{formats_html}</td>
                        <td class="available-cell">{available_html}</td>
                        <td class="actions-cell">
                            <button class="btn btn-generate" onclick="generateZip('{zip_code}')"
                                id="gen-{zip_code}">Generate Now</button>
                        </td>
                    </tr>
                ''')

            zip_table_rows = '\n'.join(zip_rows_html) if zip_rows_html else '<tr><td colspan="5"><em>No ZIP codes configured. Use the form above to add one.</em></td></tr>'

            html = render_template('admin.html', zip_table_rows=zip_table_rows)
            return Response.new(html, headers=to_js({"content-type": "text/html;charset=UTF-8"}))
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to load admin page: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _serve_guide(self):
        """Serve guide page"""
        try:
            html = load_template('guide.html')
            return Response.new(html, headers=to_js({"content-type": "text/html;charset=UTF-8"}))
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to load guide page: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _serve_css(self):
        """Serve CSS file"""
        try:
            workers_dir = os.path.dirname(__file__)
            css_path = os.path.join(workers_dir, 'assets', 'styles.css')
            with open(css_path, 'r') as f:
                css_content = f.read()

            return Response.new(css_content, headers=to_js({
                "content-type": "text/css; charset=UTF-8",
                "cache-control": "public, max-age=86400"
            }))
        except Exception as e:
            return Response.new(f'Error loading CSS: {str(e)}', {
                'status': 500,
                'headers': {'Content-Type': 'text/plain'}
            })

    async def _serve_diagram(self):
        """Serve diagram image"""
        try:
            workers_dir = os.path.dirname(__file__)
            diagram_path = os.path.join(workers_dir, 'assets', 'diagram.png')
            with open(diagram_path, 'rb') as f:
                image_bytes = f.read()

            from js import Uint8Array
            js_array = Uint8Array.new(len(image_bytes))
            for i, byte in enumerate(image_bytes):
                js_array[i] = byte

            return Response.new(js_array, headers=to_js({
                "content-type": "image/png",
                "cache-control": "public, max-age=86400"
            }))
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to load diagram: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _serve_example(self, env):
        """Serve example weather image"""
        try:
            all_zips = await get_all_zips_from_r2(env)
            if all_zips:
                example_zip = all_zips[0]
                format_info = FORMAT_CONFIGS.get(DEFAULT_FORMAT)
                extension = format_info['extension']
                mime_type = format_info['mime_type']
                key = f"{example_zip}/{DEFAULT_FORMAT}{extension}"
                r2_object = await env.WEATHER_IMAGES.get(key)

                if r2_object:
                    image_data = await r2_object.arrayBuffer()
                    return Response.new(image_data, headers=to_js({
                        "content-type": mime_type,
                        "cache-control": "public, max-age=900"
                    }))

            # Serve static fallback example
            workers_dir = os.path.dirname(__file__)
            example_path = os.path.join(workers_dir, 'assets', 'example.bmp')
            with open(example_path, 'rb') as f:
                image_bytes = f.read()

            from js import Uint8Array
            js_array = Uint8Array.new(len(image_bytes))
            for i, byte in enumerate(image_bytes):
                js_array[i] = byte

            return Response.new(js_array, headers=to_js({
                "content-type": "image/bmp",
                "cache-control": "public, max-age=900"
            }))
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to load example: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _serve_landing(self):
        """Serve landing page"""
        try:
            html = load_template('landing.html')
            return Response.new(html, headers=to_js({"content-type": "text/html;charset=UTF-8"}))
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to load page: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _serve_forecasts(self, env):
        """Serve forecasts page"""
        try:
            all_zips = await get_all_zips_from_r2(env)
            active_zips = await get_active_zips(env)
            zip_formats = await get_formats_per_zip(env)

            zip_items_html = []
            for zip_code in all_zips:
                is_active = zip_code in active_zips
                status_badge = '<span class="status-badge active">Up to date</span>' if is_active else '<span class="status-badge inactive">Not updating</span>'
                formats = zip_formats.get(zip_code, [])

                if formats:
                    format_links = []
                    for fmt in formats:
                        fmt_title = FORMAT_CONFIGS.get(fmt, {}).get('title', fmt)
                        if fmt == DEFAULT_FORMAT:
                            format_links.append(f'<a href="/{zip_code}" class="format-btn">{fmt_title}</a>')
                        else:
                            format_links.append(f'<a href="/{zip_code}?{fmt}" class="format-btn">{fmt_title}</a>')
                    formats_html = ''.join(format_links)
                else:
                    formats_html = '<span class="no-formats">No formats available</span>'

                zip_items_html.append(f'''
                    <div class="zip-card">
                        <div class="zip-card-header">
                            <div class="zip-code">{zip_code}</div>
                            {status_badge}
                        </div>
                        <div class="zip-card-formats">
                            {formats_html}
                        </div>
                    </div>
                ''')

            zip_cards = '\n'.join(zip_items_html) if zip_items_html else '<div class="no-zips">No forecasts available yet</div>'

            html = render_template('forecasts.html', zip_links=zip_cards, zip_count=len(all_zips))
            return Response.new(html, headers=to_js({"content-type": "text/html;charset=UTF-8"}))
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to load forecasts page: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _serve_image(self, env, zip_code, query_params, path_parts):
        """Serve weather image for a ZIP code"""
        try:
            # Debug: Check env
            if env is None:
                print(f"ERROR: env is None in _serve_image for zip {zip_code}")
                return Response.new(
                    json.dumps({'error': 'Internal error: environment not available'}),
                    {'status': 500, 'headers': {'Content-Type': 'application/json'}}
                )

            requested_format = DEFAULT_FORMAT

            # Check query parameters for format
            for param in query_params.keys():
                normalized = param.lower().replace('-', '_')
                if normalized in FORMAT_CONFIGS:
                    requested_format = normalized
                    break

            # Check path for format
            for part in path_parts:
                if part and part != zip_code:
                    path_part = part.replace('.png', '').replace('.bmp', '')
                    normalized = path_part.lower().replace('-', '_')
                    if normalized in FORMAT_CONFIGS:
                        requested_format = normalized
                        break

            if requested_format not in FORMAT_CONFIGS:
                requested_format = DEFAULT_FORMAT

            format_info = FORMAT_CONFIGS.get(requested_format)
            extension = format_info['extension']
            mime_type = format_info['mime_type']

            key = f"{zip_code}/{requested_format}{extension}"
            r2_object = await env.WEATHER_IMAGES.get(key)

            # Fallback to default if not found
            if r2_object is None and requested_format != DEFAULT_FORMAT:
                requested_format = DEFAULT_FORMAT
                format_info = FORMAT_CONFIGS.get(DEFAULT_FORMAT)
                extension = format_info['extension']
                mime_type = format_info['mime_type']
                key = f"{zip_code}/{requested_format}{extension}"
                r2_object = await env.WEATHER_IMAGES.get(key)

            if r2_object is None:
                return Response.new(
                    json.dumps({'error': 'Image not found. Waiting for first generation.'}),
                    {'status': 404, 'headers': {'Content-Type': 'application/json'}}
                )

            try:
                generated_at = r2_object.customMetadata['generated-at'] if r2_object.customMetadata else 'unknown'
                variant = r2_object.customMetadata.get('variant', 'unknown') if r2_object.customMetadata else 'unknown'
            except:
                generated_at = 'unknown'
                variant = 'unknown'

            image_data = await r2_object.arrayBuffer()
            return Response.new(image_data, headers=to_js({
                "content-type": mime_type,
                "cache-control": "public, max-age=900",
                "x-generated-at": generated_at,
                "x-zip-code": zip_code,
                "x-format": requested_format,
                "x-variant": variant
            }))

        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to fetch image: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _serve_status(self, env):
        """Serve status endpoint"""
        try:
            status_json = await env.CONFIG.get('status')
            status = json.loads(status_json) if status_json else {}

            fetcher_status_json = await env.CONFIG.get('fetcher_status')
            fetcher_status = json.loads(fetcher_status_json) if fetcher_status_json else {}

            active_zips = await get_active_zips(env)

            zip_metadata = {}
            for zip_code in active_zips:
                try:
                    metadata_json = await env.CONFIG.get(f'metadata:{zip_code}')
                    if metadata_json:
                        zip_metadata[zip_code] = json.loads(metadata_json)
                except:
                    pass

            response_data = {
                'status': status,
                'fetcherStatus': fetcher_status,
                'activeZips': active_zips,
                'zipMetadata': zip_metadata,
                'workerTime': datetime.utcnow().isoformat() + 'Z'
            }

            return Response.new(
                json.dumps(response_data, indent=2),
                headers=to_js({"content-type": "application/json"})
            )
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to fetch status: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _handle_activate(self, env, query_params):
        """Handle POST /admin/activate"""
        try:
            zip_code = query_params.get('zip')
            if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                return Response.new(
                    json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            active_zips = await add_zip_to_active(env, zip_code)

            return Response.new(
                json.dumps({
                    'success': True,
                    'zip': zip_code,
                    'message': f'ZIP {zip_code} added to active regeneration list',
                    'activeZips': active_zips
                }),
                headers=to_js({'Content-Type': 'application/json'})
            )
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to activate ZIP: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _handle_deactivate(self, env, query_params):
        """Handle POST /admin/deactivate"""
        try:
            zip_code = query_params.get('zip')
            if not zip_code:
                return Response.new(
                    json.dumps({'error': 'Missing ZIP code parameter'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            active_zips = await get_active_zips(env)
            if zip_code in active_zips:
                active_zips.remove(zip_code)
                await env.CONFIG.put('active_zips', json.dumps(active_zips))

            return Response.new(
                json.dumps({
                    'success': True,
                    'zip': zip_code,
                    'message': f'ZIP {zip_code} removed from active regeneration list',
                    'activeZips': active_zips
                }),
                headers=to_js({'Content-Type': 'application/json'})
            )
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to deactivate ZIP: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _handle_format_add(self, env, query_params):
        """Handle POST /admin/formats/add"""
        try:
            zip_code = query_params.get('zip')
            format_name = query_params.get('format', '').lower().replace('-', '_')

            if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                return Response.new(
                    json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            if not format_name or format_name not in FORMAT_CONFIGS:
                return Response.new(
                    json.dumps({'error': f'Invalid format. Available formats: {", ".join(FORMAT_CONFIGS.keys())}'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            formats = await add_format_to_zip(env, zip_code, format_name)

            return Response.new(
                json.dumps({
                    'success': True,
                    'zip': zip_code,
                    'format': format_name,
                    'formats': formats,
                    'message': f'Added {format_name} to {zip_code}'
                }),
                headers=to_js({'Content-Type': 'application/json'})
            )
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to add format: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _handle_format_remove(self, env, query_params):
        """Handle POST /admin/formats/remove"""
        try:
            zip_code = query_params.get('zip')
            format_name = query_params.get('format', '').lower().replace('-', '_')

            if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                return Response.new(
                    json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            if not format_name:
                return Response.new(
                    json.dumps({'error': 'Missing format parameter'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            formats = await remove_format_from_zip(env, zip_code, format_name)

            return Response.new(
                json.dumps({
                    'success': True,
                    'zip': zip_code,
                    'format': format_name,
                    'formats': formats,
                    'message': f'Removed {format_name} from {zip_code}'
                }),
                headers=to_js({'Content-Type': 'application/json'})
            )
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to remove format: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _handle_format_get(self, env, query_params):
        """Handle GET /admin/formats"""
        try:
            zip_code = query_params.get('zip')
            if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                return Response.new(
                    json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            formats = await get_formats_for_zip(env, zip_code)

            return Response.new(
                json.dumps({
                    'zip': zip_code,
                    'formats': formats,
                    'available': list(FORMAT_CONFIGS.keys())
                }),
                headers=to_js({'Content-Type': 'application/json'})
            )
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to get formats: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )

    async def _handle_generate(self, env, query_params):
        """
        Handle POST /admin/generate
        Enqueues ZIP to fetch-jobs queue for processing through the pipeline
        """
        try:
            zip_code = query_params.get('zip')
            if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                return Response.new(
                    json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )

            # Enqueue to fetch-jobs (weather-fetcher will handle the rest)
            job = {
                'zip_code': zip_code,
                'scheduled_at': datetime.utcnow().isoformat() + 'Z'
            }

            await env.FETCH_JOBS.send(job)

            return Response.new(
                json.dumps({
                    'success': True,
                    'zip': zip_code,
                    'message': f'Generation queued for ZIP {zip_code}'
                }),
                headers=to_js({'Content-Type': 'application/json'})
            )
        except Exception as e:
            return Response.new(
                json.dumps({'error': f'Failed to queue generation: {str(e)}'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )
