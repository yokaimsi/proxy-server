from flask import Flask, request, render_template
import requests
import logging
import json
from urllib.parse import urlparse
import uuid
from discord_webhook import DiscordWebhook, DiscordEmbed
from time import sleep

app = Flask(__name__)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


DISCORD_WEBHOOK_URL = ""

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/proxy', methods=['POST'])
def proxy():
    
    url = request.form.get('url')
    method = request.form.get('method', 'GET').upper()
    headers_input = request.form.get('headers', '')
    body = request.form.get('body', '')


    if not url or not url.startswith(('http://', 'https://')):
        return render_template('index.html', error='Invalid or missing URL', url=url, method=method, headers=headers_input, body=body)


    try:
        headers = json.loads(headers_input) if headers_input else {}
    except json.JSONDecodeError:
        return render_template('index.html', error='Invalid headers JSON format', url=url, method=method, headers=headers_input, body=body)


    request_id = str(uuid.uuid4())
    logger.info(f"Request ID: {request_id} | Method: {method} | URL: {url}")
    logger.info(f"Headers: {json.dumps(headers, indent=2)}")
    if body:
        logger.info(f"Body: {body}")


    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=body if body else None,
            timeout=10
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")


        webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, username="Proxy Server Bot")
        embed = DiscordEmbed(title="Proxy Request Failed", description=f"Error: {str(e)}", color="ff0000")
        embed.add_embed_field(name="Request ID", value=request_id, inline=False)
        embed.add_embed_field(name="Method", value=method, inline=True)
        embed.add_embed_field(name="URL", value=url, inline=True)
        embed.set_timestamp()
        embed.set_footer(text="Made By YokAi")
        webhook.add_embed(embed)
        sleep(1)  # Avoid rate limiting
        webhook.execute()

        return render_template('index.html', error=f'Request failed: {str(e)}', url=url, method=method, headers=headers_input, body=body)


    response_data = {
        'status': response.status_code,
        'headers': dict(response.headers),
        'body': response.text
    }


    logger.info(f"Response ID: {request_id} | Status: {response.status_code}")
    logger.info(f"Response Headers: {json.dumps(response_data['headers'], indent=2)}")
    logger.info(f"Response Body: {response_data['body']}")


    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, username="Proxy Server Bot")
    
    embed = DiscordEmbed(title="Proxy Request", color="03b2f8")
    embed.add_embed_field(name="Request ID", value=request_id, inline=False)
    embed.add_embed_field(name="Method", value=method, inline=True)
    embed.add_embed_field(name="URL", value=url, inline=True)
    embed.add_embed_field(name="Headers", value=f"```\n{json.dumps(headers, indent=2)}\n```", inline=False)
    if body:
        embed.add_embed_field(name="Body", value=f"```\n{body}\n```", inline=False)
    
    
    embed.add_embed_field(name="Response Status", value=str(response.status_code), inline=True)
    
    response_headers = json.dumps(response_data['headers'], indent=2)
    response_headers = response_headers[:1000] + "..." if len(response_headers) > 1000 else response_headers
    response_body = response_data['body']
    response_body = response_body[:1000] + "..." if len(response_body) > 1000 else response_body
    embed.add_embed_field(name="Response Headers", value=f"```\n{response_headers}\n```", inline=False)
    embed.add_embed_field(name="Response Body", value=f"```\n{response_body}\n```", inline=False)
    
    
    embed.set_timestamp()
    embed.set_footer(text="Made By YokAi")
    
    
    webhook.add_embed(embed)
    
    webhook_response = webhook.execute()
    if webhook_response.status_code not in range(200, 300):
        logger.error(f"Failed to send to Discord webhook: {webhook_response.status_code}")

    # Render the template with the response
    return render_template('index.html', response=response_data, url=url, method=method, headers=headers_input, body=body)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
