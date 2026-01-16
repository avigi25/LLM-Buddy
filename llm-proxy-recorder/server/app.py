from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import datetime
import sys
import logging

# Add the parent directory to the path so we can import from combiner2.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try to import needed functions from combiner2.py
try:
    from combiner2 import PromptRecord, PromptDatabase
    PROMPT_RECORDER_IMPORTED = True
except ImportError:
    PROMPT_RECORDER_IMPORTED = False
    print("Warning: Could not import from combiner2.py. Limited functionality will be available.")

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("prompt_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize prompt database if available
prompt_db = None
if PROMPT_RECORDER_IMPORTED:
    prompt_db = PromptDatabase()
    prompt_db.load()
    logger.info("Prompt database loaded successfully")

# Directory to store raw prompt data as backup
DATA_DIR = "prompt_data"
os.makedirs(DATA_DIR, exist_ok=True)

@app.route('/ping', methods=['GET'])
def ping():
    """Simple endpoint to check if the server is running"""
    status = {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt_recorder_available": PROMPT_RECORDER_IMPORTED,
        "prompts_recorded": len(prompt_db.prompts) if prompt_db else 0
    }
    return jsonify(status)

@app.route('/record_prompt', methods=['POST'])
def record_prompt():
    """Endpoint to record a prompt from the browser extension"""
    try:
        data = request.json
        logger.info(f"Received prompt from {data.get('llmName', 'Unknown LLM')}")
        
        # Always save raw data as backup
        timestamp = datetime.datetime.now().isoformat().replace(':', '-')
        filename = f"{timestamp}_{data.get('llmName', 'unknown')}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # If prompt recorder is available, use it to record the prompt
        if PROMPT_RECORDER_IMPORTED and prompt_db:
            # Create a new prompt record
            prompt_text = data.get('promptText', '')
            llm_used = data.get('llmName', 'Unknown LLM')
            if data.get('modelName'):
                llm_used += f" ({data.get('modelName')})"
            
            description = f"Prompt from {llm_used}"
            if data.get('pageTitle'):
                description += f" - {data.get('pageTitle')}"
                
            # Create and save the prompt record
            prompt_record = PromptRecord(prompt_text, llm_used, description)
            prompt_db.add_prompt(prompt_record)
            prompt_db.save()
            
            logger.info(f"Prompt saved to database: {description}")
            
            return jsonify({
                "success": True,
                "message": "Prompt recorded successfully",
                "prompt_id": prompt_record.id,
                "filename": filename
            })
        else:
            # Just acknowledge receipt of the data
            return jsonify({
                "success": True,
                "message": "Prompt saved as raw data",
                "filename": filename,
                "warning": "Prompt database not available, data saved as raw JSON only"
            })
            
    except Exception as e:
        logger.error(f"Error recording prompt: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/prompts', methods=['GET'])
def get_prompts():
    """Endpoint to retrieve recorded prompts"""
    if not PROMPT_RECORDER_IMPORTED or not prompt_db:
        return jsonify({
            "success": False,
            "error": "Prompt database not available"
        }), 503
    
    try:
        # Get all prompts from the database
        prompts = []
        for prompt in prompt_db.prompts:
            prompts.append({
                "id": prompt.id,
                "timestamp": prompt.timestamp.isoformat(),
                "llm_used": prompt.llm_used,
                "description": prompt.description,
                "prompt_text": prompt.prompt_text,
                "associated_files": prompt.associated_files
            })
        
        return jsonify({
            "success": True,
            "prompts": prompts
        })
    
    except Exception as e:
        logger.error(f"Error retrieving prompts: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/associate_prompt', methods=['POST'])
def associate_prompt():
    """Endpoint to associate a prompt with a file"""
    if not PROMPT_RECORDER_IMPORTED or not prompt_db:
        return jsonify({
            "success": False,
            "error": "Prompt database not available"
        }), 503
    
    try:
        data = request.json
        prompt_id = data.get('prompt_id')
        file_path = data.get('file_path')
        
        if not prompt_id or not file_path:
            return jsonify({
                "success": False,
                "error": "Missing prompt_id or file_path"
            }), 400
        
        # Find the prompt in the database
        prompt = prompt_db.get_prompt(prompt_id)
        if not prompt:
            return jsonify({
                "success": False,
                "error": f"Prompt with ID {prompt_id} not found"
            }), 404
        
        # Associate the file with the prompt
        if file_path not in prompt.associated_files:
            prompt.associated_files.append(file_path)
            prompt_db.save()
            
            logger.info(f"Associated file {file_path} with prompt {prompt_id}")
            
            return jsonify({
                "success": True,
                "message": f"File {file_path} associated with prompt {prompt_id}"
            })
        else:
            return jsonify({
                "success": True,
                "message": f"File {file_path} already associated with prompt {prompt_id}"
            })
    
    except Exception as e:
        logger.error(f"Error associating prompt with file: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


