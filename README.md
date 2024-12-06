I'll create a comprehensive documentation file for the application.

```markdown:README.md
# Image Generation Service Documentation

This service processes slide content through Anthropic's Claude AI to generate Midjourney prompts, which are then used to create images via APIframe. The service handles batch processing and provides asynchronous webhook-based responses.

## API Endpoint

- **URL**: `/`
- **Method**: `POST`
- **Content-Type**: `application/json`

## Input Schema

```json
{
    "slides": [
        {
            "slide": "string - The slide content to generate an image for"
        }
    ],
    "dest_webhook": "string - URL where the results will be sent",
    "apiframe_key": "string - Your APIframe API key",
    "anthropic_key": "string - Your Anthropic API key",
    "NameTitleofChallenge": "string - The title/name of the challenge",
    "VisualDescriptionofAvatar": "string - Description of the target audience",
    "IdealAvatar": "string - Gender and racial identity specifications"
}
```

### Required Fields
All fields mentioned above are required. The service will return a 400 error if any field is missing.

### Example Request
```json
{
    "slides": [
        {"slide": "A powerful leader speaking to a crowd"},
        {"slide": "A team collaborating in a modern office"}
    ],
    "dest_webhook": "https://your-webhook.com/endpoint",
    "apiframe_key": "your_apiframe_key",
    "anthropic_key": "your_anthropic_key",
    "NameTitleofChallenge": "Leadership Excellence Program",
    "VisualDescriptionofAvatar": "Professional executives aged 35-50",
    "IdealAvatar": "Diverse mix of genders and ethnicities"
}
```

## Output Schema

### Immediate Response
```json
{
    "status": "processing",
    "total_slides": "integer - Number of slides being processed",
    "message": "Results will be sent to the destination webhook"
}
```

### Webhook Response
The following data structure will be sent to the specified `dest_webhook`:
```json
{
    "data": [
        {
            "slide": "string - Original slide content",
            "images": ["string - Array of image URLs"],
            "prompt": "string - Generated Midjourney prompt",
            "task_id": "string - APIframe task ID",
            "status": "string - 'success' or 'timeout'",
            "error": "string - Error message (if applicable)"
        }
    ]
}
```

## How It Works

1. **Request Processing**
   - Validates incoming request for required fields
   - Extracts template data for prompt generation

2. **Prompt Generation**
   - Uses Claude AI (model: claude-3-haiku-20240229) to generate Midjourney prompts
   - Implements retry logic for 5xx errors with exponential backoff
   - Maximum 3 retry attempts with base wait time of 7 seconds

3. **Image Generation**
   - Processes slides in batches of 20 (configurable via MAX_CONCURRENT_REQUESTS)
   - Submits image generation requests to APIframe
   - Uses 21:9 aspect ratio for generated images

4. **Status Monitoring**
   - Implements batch status checking using APIframe's fetch-many endpoint
   - Polls for completion with exponential backoff
   - Maximum wait time of 120 seconds per batch
   - Poll interval starts at 10 seconds and increases up to 30 seconds

5. **Result Handling**
   - Collects results for completed tasks
   - Marks timed-out tasks appropriately
   - Sends consolidated results to the specified webhook

## Error Handling

- **Missing Fields**: Returns 400 Bad Request with details of missing fields
- **Invalid Input**: Returns 400 Bad Request for non-array slides
- **API Errors**: 
  - Implements retry logic for Anthropic API 5xx errors
  - Tracks failed image generations
  - Reports timeouts for tasks exceeding wait time
- **Webhook Errors**: Logs webhook delivery failures

## Technical Details

- Built with Flask and async/await for concurrent processing
- Uses aiohttp for asynchronous HTTP requests
- Implements exponential backoff for retries
- Handles concurrent processing of multiple slides
- Provides real-time status updates via webhook

## Limitations

- Maximum wait time of 120 seconds per batch
- Maximum 20 concurrent requests (configurable)
- Webhook must be able to handle POST requests with JSON payload
- Requires valid API keys for both Anthropic and APIframe services
```

This documentation provides a comprehensive overview of the service's functionality, input/output formats, and operational details. You may want to add additional sections specific to your deployment environment, such as:

1. Deployment instructions
2. Environment variable configuration
3. Monitoring and logging details
4. Rate limiting information
5. Security considerations

Let me know if you'd like me to expand on any of these aspects.
