from flask import Flask, request, jsonify
from openai import OpenAI
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('sms_bridge.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load configuration from environment variables
TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE = os.getenv('TWILIO_PHONE')
XAI_API_KEY = os.getenv('XAI_API_KEY')
xai_client = OpenAI(base_url="https://api.x.ai/v1", api_key=XAI_API_KEY)

# Validate configuration
print(f"\n{'='*60}")
print(f"🔧 Configuration Check:")
print(f"   📱 Twilio Phone: {TWILIO_PHONE or '❌ Not configured'}")
print(f"   🆔 Twilio SID: {TWILIO_SID[:10] + '...' if TWILIO_SID else '❌ Not configured'}")
print(f"   🔑 xAI API Key: {XAI_API_KEY[:10] + '...' if XAI_API_KEY else '❌ Not configured'}")
print(f"{'='*60}")

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return handle_sms_webhook()
    return """
    <h1>SMS Bridge with Grok AI</h1>
    <p>✅ Application is running!</p>
    <p>🧪 <a href="/test">Test SMS</a></p>
    <p>📊 <a href="/logs">View Logs</a></p>
    <p>🔧 <a href="/status">System Status</a></p>
    <p>🏥 <a href="/health">Health Check</a></p>
    <p><strong>📡 Webhook URL:</strong> <code>http://your_ip:5001/</code></p>
    """

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "SMS Bridge",
        "endpoints": {
            "sms_webhook": "/",
            "home": "/",
            "test": "/test",
            "logs": "/logs",
            "status": "/status"
        }
    })

@app.route('/test')
def test_sms():
    return f"""
    <h2>Test SMS Endpoint</h2>
    <p>Test with custom messages:</p>
    
    <h3>Quick Test with "hi":</h3>
    <form action="/" method="post" style="margin-bottom: 20px;">
        <input type="hidden" name="Body" value="hi">
        <input type="hidden" name="From" value="+15551234567">
        <input type="hidden" name="To" value="{TWILIO_PHONE}">
        <button type="submit" style="padding: 10px 20px; font-size: 16px; background: #28a745; color: white; border: none; border-radius: 5px;">
            🧪 Test with "hi"
        </button>
    </form>
    
    <h3>Custom Message Test:</h3>
    <form action="/" method="post">
        <label for="message">Message:</label><br>
        <input type="text" id="message" name="Body" value="Hello from web test" style="width: 300px; padding: 8px; margin: 5px 0;"><br>
        <input type="hidden" name="From" value="+15551234567">
        <input type="hidden" name="To" value="{TWILIO_PHONE}">
        <button type="submit" style="padding: 10px 20px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 5px; margin-top: 10px;">
            🧪 Send Custom Message
        </button>
    </form>
    
    <p><a href="/">← Back to Home</a></p>
    """

@app.route('/logs')
def view_logs():
    try:
        with open('sms_bridge.log', 'r') as f:
            logs = f.readlines()
        # Show last 50 lines
        recent_logs = logs[-50:] if len(logs) > 50 else logs
        return f"""
        <h2>Recent Logs (Last 50 lines)</h2>
        <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto;">
{''.join(recent_logs)}
        </pre>
        <p><a href="/">← Back to Home</a></p>
        """
    except FileNotFoundError:
        return "<h2>No logs found</h2><p>Log file doesn't exist yet.</p><p><a href='/'>← Back to Home</a></p>"

@app.route('/status')
def system_status():
    return f"""
    <h2>System Status</h2>
    <p><strong>Environment:</strong> {'Production' if not app.debug else 'Development'}</p>
    <p><strong>Debug Mode:</strong> {app.debug}</p>
    <p><strong>Twilio SID:</strong> {TWILIO_SID[:10] + '...' if TWILIO_SID else '❌ Not configured'}</p>
    <p><strong>Twilio Phone:</strong> {TWILIO_PHONE or '❌ Not configured'}</p>
    <p><strong>xAI API Key:</strong> {XAI_API_KEY[:10] + '...' if XAI_API_KEY else '❌ Not configured'}</p>
    <p><a href="/">← Back to Home</a></p>
    """

def handle_sms_webhook():
    """Handle incoming SMS webhook requests"""
    form_keys = list(request.form.keys())
    
    # Check for Twilio status callbacks (delivery status updates)
    if 'MessageStatus' in request.form:
        message_sid = request.form.get('MessageSid', 'Unknown')
        status = request.form.get('MessageStatus', 'Unknown')
        print(f"📩 Twilio Status Callback - SID: {message_sid}, Status: {status}")
        logger.info(f"📩 Twilio Status Callback - SID: {message_sid}, Status: {status}")
        return "Status received", 200  # Acknowledge without error
    
    # Validate required form data for SMS
    if 'Body' not in request.form or 'From' not in request.form:
        print(f"⚠️ Invalid webhook request - missing required fields")
        print(f"   Available fields: {form_keys}")
        logger.warning(f"Invalid webhook request - missing required fields: {form_keys}")
        return "Invalid request", 400
    
    # Log incoming SMS details
    user_message = request.form['Body']  # Incoming SMS text
    user_number = request.form['From'].strip()   # User's phone number (clean spaces)
    timestamp = datetime.now().isoformat()
    
    # Console output for immediate visibility
    print(f"\n{'='*60}")
    print(f"📱 SMS RECEIVED at {datetime.now().strftime('%H:%M:%S')}")
    print(f"📞 From: {user_number}")
    print(f"💬 Message: {user_message}")
    print(f"📤 Will reply to: {user_number}")
    print(f"📱 Using Twilio number: {TWILIO_PHONE}")
    print(f"{'='*60}")
    
    logger.info(f"📱 SMS RECEIVED - From: {user_number}, Time: {timestamp}")
    logger.info(f"📝 Message Content: {user_message}")
    
    # Test mode: Skip xAI and use fake response
    TEST_MODE = False  # Set to True for fake responses, False for real Grok
    
    if TEST_MODE:
        print(f"🧪 TEST MODE: Using fake response instead of xAI")
        ai_reply = f"🧪 TEST MODE: You said '{user_message}'. This is a test response to verify SMS delivery. Your message was received and processed successfully!"
        api_duration = 0.0
        print(f"🤖 Fake Response: {ai_reply}")
        logger.info(f"🧪 TEST MODE: Using fake response")
    else:
        # Log xAI API call attempt
        print(f"🤖 Calling xAI API (grok-4)...")
        logger.info(f"🤖 Calling xAI API with model: grok-4")
        
        # Call Grok API for response
        try:
            api_start_time = datetime.now()
            response = xai_client.chat.completions.create(
                model="grok-4",  # Or "grok-3-mini" for cheaper
                messages=[{"role": "user", "content": user_message}],
                max_tokens=2000,  # Increased to 2000 for much more complete responses
                temperature=0.7  # Adjust for creativity
            )
            api_end_time = datetime.now()
            api_duration = (api_end_time - api_start_time).total_seconds()
            
            ai_reply = response.choices[0].message.content.strip()
            finish_reason = response.choices[0].finish_reason
            
            # Debug: Print full response structure
            print(f"🔍 Debug - Full response structure:")
            print(f"   Response type: {type(response)}")
            print(f"   Choices count: {len(response.choices)}")
            print(f"   First choice: {response.choices[0] if response.choices else 'None'}")
            print(f"   Finish reason: {finish_reason}")
            print(f"   Message content: {repr(ai_reply)}")
            
            # Handle truncated responses - use what we got!
            if finish_reason == 'length':
                print(f"⚠️ Response was truncated (finish_reason: {finish_reason})")
                print(f"🔄 Using truncated response - it's still good content!")
                # Keep the truncated response - don't replace it!
            elif not ai_reply:
                print(f"⚠️ Empty response received")
                ai_reply = "Sorry, I couldn't generate a response. Please try again."
                print(f"🔄 Using fallback response: {ai_reply}")
            
            # Console output for successful API call
            print(f"✅ xAI API SUCCESS ({api_duration:.2f}s)")
            print(f"🤖 AI Response: {ai_reply}")
            
            # Log successful API response
            logger.info(f"✅ xAI API SUCCESS - Duration: {api_duration:.2f}s, Tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
            logger.info(f"📝 AI Response: {ai_reply}")
            
        except Exception as e:
            api_end_time = datetime.now()
            api_duration = (api_end_time - api_start_time).total_seconds() if 'api_start_time' in locals() else 0
            
            ai_reply = "Sorry, there was an error. Try again!"
            
            # Console output for API error
            print(f"❌ xAI API ERROR ({api_duration:.2f}s)")
            print(f"🔍 Error: {str(e)}")
            
            logger.error(f"❌ xAI API ERROR - Duration: {api_duration:.2f}s, Error: {str(e)}")
            logger.error(f"🔍 Full error details: {type(e).__name__}: {str(e)}")

    # Handle SMS length with smart chunking
    MAX_SMS_LENGTH = 1440  # Twilio's recommended limit for SMS
    ai_replies = []
    
    if len(ai_reply) <= MAX_SMS_LENGTH:
        ai_replies = [ai_reply]
    else:
        # Split into multiple SMS messages
        words = ai_reply.split()
        current_chunk = ""
        
        for word in words:
            if len(current_chunk + " " + word) <= MAX_SMS_LENGTH:
                current_chunk += (" " + word) if current_chunk else word
            else:
                if current_chunk:
                    ai_replies.append(current_chunk.strip())
                current_chunk = word
        
        if current_chunk:
            ai_replies.append(current_chunk.strip())
        
        print(f"📱 Splitting response into {len(ai_replies)} SMS messages:")
        for i, chunk in enumerate(ai_replies, 1):
            print(f"   📝 Part {i}: {len(chunk)} chars")
        logger.info(f"📱 Response split into {len(ai_replies)} SMS messages")

    # Log Twilio SMS sending attempt
    print(f"📤 Sending SMS reply to {user_number}...")
    logger.info(f"📤 Sending SMS reply to {user_number}")
    
    # Send reply back via Twilio (handling multiple chunks)
    try:
        twilio_start_time = datetime.now()
        twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        # Clean phone number for Twilio
        clean_user_number = user_number.strip()
        print(f"📱 Sending to cleaned number: '{clean_user_number}'")
        
        # Send each chunk as a separate SMS
        sent_messages = []
        for i, chunk in enumerate(ai_replies, 1):
            if len(ai_replies) > 1:
                # Add part indicator for multi-part messages
                formatted_chunk = f"({i}/{len(ai_replies)}) {chunk}"
            else:
                formatted_chunk = chunk
            
            print(f"📤 Sending part {i}/{len(ai_replies)} ({len(chunk)} chars)...")
            
            twilio_message = twilio_client.messages.create(
                body=formatted_chunk,
                from_=TWILIO_PHONE,
                to=clean_user_number
            )
            sent_messages.append(twilio_message.sid)
            print(f"✅ Part {i} sent - SID: {twilio_message.sid}")
        
        twilio_end_time = datetime.now()
        twilio_duration = (twilio_end_time - twilio_start_time).total_seconds()
        
        # Console output for successful SMS
        if len(ai_replies) == 1:
            print(f"✅ SMS SENT ({twilio_duration:.2f}s)")
            print(f"🆔 Twilio SID: {sent_messages[0]}")
        else:
            print(f"✅ {len(ai_replies)} SMS messages sent ({twilio_duration:.2f}s)")
            print(f"🆔 Twilio SIDs: {', '.join(sent_messages)}")
        
        logger.info(f"✅ Twilio SMS SENT - Duration: {twilio_duration:.2f}s, Messages: {len(ai_replies)}, SIDs: {sent_messages}")
        
    except Exception as e:
        twilio_end_time = datetime.now()
        twilio_duration = (twilio_end_time - twilio_start_time).total_seconds() if 'twilio_start_time' in locals() else 0
        
        # Console output for SMS error
        print(f"❌ SMS SENDING FAILED ({twilio_duration:.2f}s)")
        print(f"🔍 Error: {str(e)}")
        
        logger.error(f"❌ Twilio SMS ERROR - Duration: {twilio_duration:.2f}s, Error: {str(e)}")
        logger.error(f"🔍 Twilio error details: {type(e).__name__}: {str(e)}")

    # Log webhook completion
    total_duration = (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds()
    
    # Console output for completion
    print(f"🏁 Webhook completed in {total_duration:.2f}s")
    print(f"{'='*60}\n")
    
    logger.info(f"🏁 Webhook completed in {total_duration:.2f}s for {user_number}")
    logger.info("=" * 80)
    
    # Return TwiML (empty response to acknowledge webhook)
    resp = MessagingResponse()
    return str(resp)

# Removed legacy '/sms' endpoint; Twilio should post to root '/'

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"🚀 SMS Bridge with Grok AI Starting...")
    print(f"📱 SMS Webhook: http://0.0.0.0:5001/ (POST)")
    print(f"🌐 Home Page: http://localhost:5001/ (GET)")
    print(f"🧪 Test: http://localhost:5001/test")
    print(f"📊 Logs: http://localhost:5001/logs")
    print(f"🔧 Status: http://localhost:5001/status")
    print(f"{'='*60}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"\n💡 To test SMS endpoint from terminal:")
    print(f"   curl -X POST http://localhost:5001/ \\")
    print(f"     -d 'Body=Hello from curl test' \\")
    print(f"     -d 'From=+15551234567' \\")
    print(f"     -d 'To={TWILIO_PHONE}'")
    print(f"\n💡 Or test from external network:")
    print(f"   curl -X POST http://your_ip:5001/ \\")
    print(f"     -d 'Body=Hello from internet' \\")
    print(f"     -d 'From=+15551234567' \\")
    print(f"     -d 'To={TWILIO_PHONE}'")
    print(f"{'='*60}\n")
    
    app.run(debug=True, port=5001, host='0.0.0.0')