# Cloudflare Storage Guide for Weather Landscape Worker

## Overview

This Weather Landscape Worker uses two Cloudflare storage systems:

1. **R2 Bucket** (`weather-landscapes`) - Stores generated PNG weather images
2. **KV Namespace** (`weather-config`) - Stores configuration and metadata

This guide explains how to access and use both storage systems when building the Python worker.

---

## R2 Bucket: `weather-landscapes`

### What It Is

R2 is Cloudflare's S3-compatible object storage. Think of it as a file system in the cloud where we store our generated weather landscape images.

### Purpose

- **Primary:** Stores `current.png` (always the latest weather landscape)
- **Archive:** Stores timestamped images in `YYYY-MM-DD/HH-mm.png` format
- **Organization:** Files organized by ZIP code (e.g., `78729/current.png`)

### How to Access It

#### In Cloudflare Worker (JavaScript)

The bucket is bound to your worker environment as `WEATHER_IMAGES`:

```javascript
// In your worker code (src/index.js)
export default {
  async scheduled(event, env, ctx) {
    // Upload image to R2
    await env.WEATHER_IMAGES.put(
      '78729/current.png',
      imageBuffer,
      {
        httpMetadata: {
          contentType: 'image/png',
        },
        customMetadata: {
          generatedAt: new Date().toISOString(),
          weatherCode: '01d',
          temperature: '72',
        },
      }
    );
    
    // Retrieve image from R2
    const image = await env.WEATHER_IMAGES.get('78729/current.png');
    const imageBytes = await image.arrayBuffer();
    
    // List all files for a ZIP code
    const list = await env.WEATHER_IMAGES.list({ prefix: '78729/' });
    console.log('Files:', list.objects.map(obj => obj.key));
  }
};
```

#### For Python Worker Development

When building the Python worker that generates images, you'll need to:

**1. Generate the PNG image** (using your Python canvas/PIL code)

**2. Upload it to R2** via the Cloudflare API or S3-compatible interface:

```python
import boto3
from botocore.config import Config

# Configure S3-compatible client for R2
s3 = boto3.client(
    's3',
    endpoint_url=f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id='YOUR_R2_ACCESS_KEY_ID',
    aws_secret_access_key='YOUR_R2_SECRET_ACCESS_KEY',
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

# Upload image
with open('weather_landscape.png', 'rb') as f:
    s3.put_object(
        Bucket='weather-landscapes',
        Key='78729/current.png',
        Body=f.read(),
        ContentType='image/png',
        Metadata={
            'generated-at': '2025-01-10T12:00:00Z',
            'weather-code': '01d',
            'temperature': '72'
        }
    )

# Download image
response = s3.get_object(Bucket='weather-landscapes', Key='78729/current.png')
image_bytes = response['Body'].read()

# List files
response = s3.list_objects_v2(Bucket='weather-landscapes', Prefix='78729/')
for obj in response.get('Contents', []):
    print(f"Found: {obj['Key']}")
```

**Important:** You'll need R2 API credentials. These can be created in the Cloudflare Dashboard:
- Go to R2 → Manage R2 API Tokens
- Create API Token with "Object Read & Write" permissions
- Save `Access Key ID` and `Secret Access Key`

### File Structure

```
weather-landscapes/
├── 78729/
│   ├── current.png                    # Always the latest image
│   ├── latest.json                    # Metadata about current image
│   └── archive/
│       └── 2025-01-10/
│           ├── 12-00.png             # Timestamped backup
│           └── 12-15.png             # Timestamped backup
└── {other-zip-codes}/
    └── ...
```

### File Naming Convention

- **Current image:** `{zipcode}/current.png`
- **Archive images:** `{zipcode}/archive/{YYYY-MM-DD}/{HH-mm}.png`
- **Metadata:** `{zipcode}/latest.json`

### Metadata Example (`latest.json`)

```json
{
  "generatedAt": "2025-01-10T12:00:00Z",
  "zipCode": "78729",
  "location": {
    "latitude": 30.4643,
    "longitude": -97.8035,
    "city": "Austin",
    "state": "TX"
  },
  "weather": {
    "temperature": 72,
    "weatherCode": "01d",
    "cloudCover": 20,
    "windSpeed": 12,
    "windDirection": 180,
    "precipitation": 0
  },
  "imageUrl": "https://weather-landscapes.{account-id}.r2.cloudflarestorage.com/78729/current.png",
  "fileSize": 95432
}
```

---

## KV Namespace: `weather-config`

### What It Is

KV (Key-Value) is Cloudflare's globally distributed key-value data store. It's perfect for storing configuration data, coordinates, and small metadata.

### Purpose

- **Location data:** ZIP code → latitude/longitude mapping
- **User preferences:** Display settings, update frequency
- **Cache:** Last successful API response (fallback)
- **Timestamps:** Track last update, error counts

### How to Access It

#### In Cloudflare Worker (JavaScript)

The KV namespace is bound to your worker as `CONFIG`:

```javascript
// In your worker code (src/index.js)
export default {
  async scheduled(event, env, ctx) {
    // Store configuration
    await env.CONFIG.put(
      'location:78729',
      JSON.stringify({
        latitude: 30.4643,
        longitude: -97.8035,
        city: 'Austin',
        state: 'TX',
        timezone: 'America/Chicago'
      })
    );
    
    // Retrieve configuration
    const locationData = await env.CONFIG.get('location:78729', 'json');
    console.log('Location:', locationData);
    
    // Store with expiration (auto-delete after 7 days)
    await env.CONFIG.put(
      'cache:weather:78729',
      JSON.stringify(weatherData),
      { expirationTtl: 7 * 24 * 60 * 60 }
    );
    
    // List all keys
    const keys = await env.CONFIG.list({ prefix: 'location:' });
    console.log('All locations:', keys.keys.map(k => k.name));
  }
};
```

#### For Python Worker Development

When building the Python worker, you'll access KV via the Cloudflare API:

```python
import requests

# Cloudflare API credentials
ACCOUNT_ID = 'your-account-id'
NAMESPACE_ID = 'e7c9b116911d484a9c7a2f9819e00e5a'  # From wrangler.toml
API_TOKEN = 'your-cloudflare-api-token'

BASE_URL = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}'

headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

# Write to KV
def put_kv(key, value):
    url = f'{BASE_URL}/values/{key}'
    response = requests.put(url, headers=headers, json=value)
    return response.json()

# Read from KV
def get_kv(key):
    url = f'{BASE_URL}/values/{key}'
    response = requests.get(url, headers=headers)
    return response.json()

# Example: Store location data
location_data = {
    'latitude': 30.4643,
    'longitude': -97.8035,
    'city': 'Austin',
    'state': 'TX'
}
put_kv('location:78729', location_data)

# Example: Retrieve location data
location = get_kv('location:78729')
print(f"Generating weather for {location['city']}, {location['state']}")
```

**Important:** You'll need a Cloudflare API Token:
- Go to My Profile → API Tokens
- Create Token with "Account.Workers KV Storage" permissions
- Save the token securely

### Key Naming Conventions

Use prefixes to organize data:

- `location:{zipcode}` - Location coordinates
- `config:global` - Global settings
- `cache:weather:{zipcode}` - Cached weather data
- `status:{zipcode}` - Last update status
- `error:{zipcode}` - Error tracking

### Data Schema Examples

#### Location Data

```json
{
  "key": "location:78729",
  "value": {
    "latitude": 30.4643,
    "longitude": -97.8035,
    "city": "Austin",
    "state": "TX",
    "country": "US",
    "timezone": "America/Chicago"
  }
}
```

#### Global Configuration

```json
{
  "key": "config:global",
  "value": {
    "imageWidth": 1920,
    "imageHeight": 1080,
    "updateInterval": 15,
    "archiveRetentionDays": 7,
    "enableArchive": true
  }
}
```

#### Cached Weather Data (Fallback)

```json
{
  "key": "cache:weather:78729",
  "value": {
    "fetchedAt": "2025-01-10T12:00:00Z",
    "hourly": {
      "time": ["2025-01-10T12:00", "2025-01-10T13:00"],
      "temperature_2m": [72, 73],
      "precipitation": [0, 0],
      "cloudcover": [20, 30],
      "windspeed_10m": [12, 13],
      "winddirection_10m": [180, 185],
      "weathercode": [1, 2]
    }
  },
  "expirationTtl": 604800  // 7 days
}
```

#### Status Tracking

```json
{
  "key": "status:78729",
  "value": {
    "lastSuccess": "2025-01-10T12:00:00Z",
    "lastError": null,
    "errorCount": 0,
    "consecutiveErrors": 0,
    "totalGenerations": 2847
  }
}
```

---

## Wrangler Configuration

The worker is configured in `wrangler.toml`:

```toml
name = "weather-landscape-worker"
main = "src/index.js"
compatibility_date = "2025-01-10"

# Cron Trigger - runs every 15 minutes
[triggers]
crons = ["*/15 * * * *"]

# R2 Bucket Binding
[[r2_buckets]]
binding = "WEATHER_IMAGES"              # Access as env.WEATHER_IMAGES
bucket_name = "weather-landscapes"      # Actual bucket name

# KV Namespace Binding  
[[kv_namespaces]]
binding = "CONFIG"                      # Access as env.CONFIG
id = "e7c9b116911d484a9c7a2f9819e00e5a"  # Namespace ID

# Environment Variables
[vars]
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
DEFAULT_ZIP = "78729"
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
```

---

## Workflow: Python Worker Integration

### Step 1: Generate Weather Landscape (Python)

Your Python code will:

1. Fetch weather data from Open-Meteo API
2. Generate landscape visualization using PIL/Canvas
3. Save as PNG to file or buffer

```python
# Your existing Python code
from p_weather.draw_weather import generate_weather_landscape

# Generate image
image_buffer = generate_weather_landscape(
    zip_code='78729',
    weather_data=fetch_weather_data()
)
```

### Step 2: Upload to R2

```python
# Upload to Cloudflare R2
s3.put_object(
    Bucket='weather-landscapes',
    Key='78729/current.png',
    Body=image_buffer,
    ContentType='image/png'
)
```

### Step 3: Update KV Metadata

```python
# Store metadata in KV
put_kv('status:78729', {
    'lastSuccess': datetime.now().isoformat(),
    'errorCount': 0,
    'fileSize': len(image_buffer)
})
```

### Step 4: Cloudflare Worker Serves Image

The JavaScript worker (already deployed) will:

1. Receive HTTP request for `GET /78729/current.png`
2. Fetch image from R2 via `env.WEATHER_IMAGES`
3. Return image to client

```javascript
// This is already handled by the deployed worker
async fetch(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.slice(1); // Remove leading /
  
  const image = await env.WEATHER_IMAGES.get(path);
  if (!image) {
    return new Response('Image not found', { status: 404 });
  }
  
  return new Response(image.body, {
    headers: {
      'Content-Type': 'image/png',
      'Cache-Control': 'public, max-age=900', // 15 minutes
    },
  });
}
```

---

## Getting API Credentials

### R2 Access Keys

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Go to **R2** → **Overview**
3. Click **Manage R2 API Tokens**
4. Click **Create API Token**
5. Select permissions: **Object Read & Write**
6. Choose bucket: `weather-landscapes`
7. Save your **Access Key ID** and **Secret Access Key**

### Cloudflare API Token

1. Go to **My Profile** → **API Tokens**
2. Click **Create Token**
3. Use template: **Edit Cloudflare Workers**
4. Add permissions:
   - Account → Workers KV Storage → Edit
   - Account → Workers Scripts → Edit
5. Save your **API Token**

---

## Testing Locally

### Test R2 Upload (Python)

```python
# test_r2_upload.py
import boto3
from PIL import Image
import io

# Configure R2 client
s3 = boto3.client(
    's3',
    endpoint_url=f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='auto'
)

# Create test image
img = Image.new('RGB', (1920, 1080), color='red')
buffer = io.BytesIO()
img.save(buffer, format='PNG')
buffer.seek(0)

# Upload to R2
s3.put_object(
    Bucket='weather-landscapes',
    Key='test/demo.png',
    Body=buffer.getvalue(),
    ContentType='image/png'
)

print('✅ Upload successful!')
```

### Test KV Write (Python)

```python
# test_kv_write.py
import requests

NAMESPACE_ID = 'e7c9b116911d484a9c7a2f9819e00e5a'
API_TOKEN = 'YOUR_API_TOKEN'

url = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/test-key'
headers = {'Authorization': f'Bearer {API_TOKEN}'}

response = requests.put(url, headers=headers, json={'message': 'Hello from Python!'})
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
```

---

## Common Issues & Solutions

### Issue: "Access Denied" when uploading to R2

**Solution:** Make sure your R2 API token has **Object Read & Write** permissions for the `weather-landscapes` bucket.

### Issue: "Namespace not found" in KV

**Solution:** Verify the namespace ID `e7c9b116911d484a9c7a2f9819e00e5a` is correct in your API calls.

### Issue: Image not appearing on worker URL

**Solution:** 
- Verify image was uploaded successfully to R2
- Check file path matches expected format: `{zipcode}/current.png`
- Ensure worker is deployed and cron is running

### Issue: KV data not persisting

**Solution:** KV writes can take up to 60 seconds to propagate globally. Use `await` in async contexts.

---

## Storage Limits & Pricing

### R2 (Object Storage)

**Free Tier:**
- ✅ 10 GB storage/month
- ✅ 1 million Class A operations (writes) /month
- ✅ 10 million Class B operations (reads) /month
- ✅ Zero egress fees

**Our Usage:**
- ~100 KB per image × 2,880 images/month = 280 MB
- **Cost: $0/month** ✅

### KV (Key-Value Store)

**Free Tier:**
- ✅ 100,000 reads/day
- ✅ 1,000 writes/day
- ✅ 1 GB storage

**Our Usage:**
- ~10 KB of config data
- ~96 reads/day (cron triggers)
- ~5 writes/day
- **Cost: $0/month** ✅

---

## Security Best Practices

1. **Never commit API credentials** to version control
2. Use environment variables for secrets
3. Rotate API tokens every 90 days
4. Use least-privilege permissions (only what you need)
5. Enable audit logging in Cloudflare Dashboard
6. Use Wrangler Secrets for sensitive data in workers:
   ```bash
   wrangler secret put R2_ACCESS_KEY_ID
   wrangler secret put R2_SECRET_ACCESS_KEY
   ```

---

## Additional Resources

- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [Cloudflare Workers KV Documentation](https://developers.cloudflare.com/kv/)
- [Boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [Cloudflare API Documentation](https://developers.cloudflare.com/api/)

---

## Questions?

If you need help accessing the bucket or KV store, reach out with specifics about what you're trying to do and any error messages you're seeing.

**Happy coding! 🎨☁️**
