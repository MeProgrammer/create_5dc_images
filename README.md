# Image Generation Service Documentation

This service processes slide content through Anthropic's Claude AI to generate Midjourney prompts, which are then used to create images via APIframe. The service handles batch processing and provides asynchronous webhook-based responses.

## API Endpoint

- **URL**: `/`
- **Method**: `POST`
- **Content-Type**: `application/json`

## Input Schema 