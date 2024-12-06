from flask import Flask, request, jsonify
import asyncio
import aiohttp
import os
from anthropic import Anthropic
from dotenv import load_dotenv
from functools import partial

load_dotenv()

app = Flask(__name__)

MAX_CONCURRENT_REQUESTS = 20

def create_anthropic_prompt(slide_data, template_data):
    """Create the prompt for Anthropic using the template and data"""
    prompt_template = """here is the info you need to create the midjourney prompt

the product we are offering is 
{NameTitleofChallenge}

procuct bio n/a

my target audience {VisualDescriptionofAvatar}

my ideal gender for my image is {IdealAvatar}

the racial identity of my images is: {IdealAvatar}

you are creating an image that must be in alignment with this {slide}"""

    # Prepare the template data
    format_data = {
        'NameTitleofChallenge': template_data.get('NameTitleofChallenge', 'N/A'),
        'VisualDescriptionofAvatar': template_data.get('VisualDescriptionofAvatar', 'N/A'),
        'IdealAvatar': template_data.get('IdealAvatar', 'N/A'),
        'slide': slide_data.get('slide', 'N/A')
    }

    return prompt_template.format(**format_data)

async def generate_midjourney_prompt(anthropic_client, slide_data, template_data):
    """Generate a Midjourney prompt using Anthropic"""
    max_attempts = 3
    base_wait_time = 7  # seconds
    
    for attempt in range(max_attempts):
        try:
            prompt = create_anthropic_prompt(slide_data, template_data)
            assistant_prompt = """You are an expert at creating Midjourney prompts.
Your task is to take the provided information and create a detailed, creative Midjourney prompt.
Focus on visual elements, style, mood, and technical aspects that will generate an engaging image.
Keep the prompt concise but descriptive.
Do not include any explanations - only output the prompt itself."""

            message = anthropic_client.messages.create(
                model="claude-3-haiku-20240229",
                max_tokens=8000,
                messages=[
                    {
                        "role": "system",
                        "content": assistant_prompt
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            return message.content[0].text
            
        except Exception as e:
            if str(e).startswith('5'):  # Check if it's a 5xx error
                if attempt < max_attempts - 1:  # Don't wait after the last attempt
                    wait_time = base_wait_time * (2 ** attempt)  # Exponential backoff
                    print(f"Attempt {attempt + 1} failed with 5xx error. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
            print(f"Error generating prompt: {str(e)}")
            return None

async def fetch_completed_tasks(session, task_ids, apiframe_key):
    """Fetch status of multiple tasks using fetch-many endpoint"""
    headers = {
        "Authorization": apiframe_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "task_ids": task_ids
    }
    
    try:
        async with session.post(
            "https://api.apiframe.pro/fetch-many",
            json=payload,
            headers=headers
        ) as response:
            results = await response.json()
            return results
    except Exception as e:
        print(f"Error fetching tasks: {str(e)}")
        return {}

async def process_slides_batch(session, slides, anthropic_client, apiframe_key, webhook_url, template_data):
    """Process a batch of slides concurrently"""
    # Generate prompts first
    prompts = []
    for slide in slides:
        prompt = await generate_midjourney_prompt(anthropic_client, slide, template_data)
        if prompt:
            prompts.append((slide, prompt))
    
    # Submit all imagine requests
    imagine_tasks = []
    for _, prompt in prompts:
        headers = {
            "Authorization": apiframe_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "aspect_ratio": "21:9",
        }
        
        try:
            async with session.post(
                "https://api.apiframe.pro/imagine",
                json=payload,
                headers=headers
            ) as response:
                result = await response.json()
                imagine_tasks.append({
                    'task_id': result.get('task_id'),
                    'prompt': prompt,
                    'slide': _
                })
        except Exception as e:
            print(f"Error submitting imagine request: {str(e)}")
    
    # Poll for completion with fetch-many
    max_wait_time = 120  # Maximum wait time in seconds
    wait_time = 0
    poll_interval = 10  # Start polling every 10 seconds
    
    pending_tasks = {task['task_id']: task for task in imagine_tasks if task.get('task_id')}
    completed_results = []
    
    while pending_tasks and wait_time < max_wait_time:
        # Wait before polling
        await asyncio.sleep(poll_interval)
        wait_time += poll_interval
        
        # Fetch status for all pending tasks
        fetch_results = await fetch_completed_tasks(
            session,
            list(pending_tasks.keys()),
            apiframe_key
        )
        
        # Process results
        for task_id, result in fetch_results.items():
            if result.get('status') == 'completed':
                task_info = pending_tasks[task_id]
                completed_results.append({
                    'slide': task_info['slide']['slide'],
                    'prompt': task_info['prompt'],
                    'images': result.get('image_urls', []),
                    'task_id': task_id,
                    'status': 'success'
                })
                del pending_tasks[task_id]
        
        # Increase polling interval with exponential backoff
        poll_interval = min(poll_interval * 1.5, 30)
    
    # Handle remaining tasks that timed out
    for task_id, task_info in pending_tasks.items():
        completed_results.append({
            'slide': task_info['slide']['slide'],
            'prompt': task_info['prompt'],
            'images': [],
            'task_id': task_id,
            'status': 'timeout',
            'error': 'Image generation timed out'
        })
    
    return completed_results

async def process_all_slides(slides, anthropic_key, apiframe_key, webhook_url, template_data):
    """Process all slides in batches of MAX_CONCURRENT_REQUESTS"""
    anthropic_client = Anthropic(api_key=anthropic_key)
    
    async with aiohttp.ClientSession() as session:
        results = []
        for i in range(0, len(slides), MAX_CONCURRENT_REQUESTS):
            batch = slides[i:i + MAX_CONCURRENT_REQUESTS]
            batch_results = await process_slides_batch(
                session, 
                batch, 
                anthropic_client, 
                apiframe_key, 
                webhook_url,
                template_data
            )
            results.extend(batch_results)
        return results

async def send_webhook_response(webhook_url, data):
    """Send processed results to the destination webhook"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(webhook_url, json={'data': data}) as response:
                return await response.json()
        except Exception as e:
            print(f"Error sending webhook: {str(e)}")
            return None

@app.route('/', methods=['POST'])
async def process_slides():
    try:
        data = request.get_json()
        required_fields = [
            'slides', 'dest_webhook', 'apiframe_key', 'anthropic_key',
            'NameTitleofChallenge', 'VisualDescriptionofAvatar', 'IdealAvatar'
        ]
        
        if not all(field in data for field in required_fields):
            return jsonify({
                'error': f'Missing required fields. Expected: {", ".join(required_fields)}'
            }), 400

        if not isinstance(data['slides'], list):
            return jsonify({'error': 'Slides must be an array'}), 400

        # Extract template data
        template_data = {
            'NameTitleofChallenge': data['NameTitleofChallenge'],
            'VisualDescriptionofAvatar': data['VisualDescriptionofAvatar'],
            'IdealAvatar': data['IdealAvatar']
        }

        results = await process_all_slides(
            data['slides'],
            data['anthropic_key'],
            data['apiframe_key'],
            data['dest_webhook'],
            template_data
        )
        
        # Send results to destination webhook
        await send_webhook_response(data['dest_webhook'], results)
        
        # Return immediate response
        return jsonify({
            'status': 'processing',
            'total_slides': len(data['slides']),
            'message': 'Results will be sent to the destination webhook'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080) 