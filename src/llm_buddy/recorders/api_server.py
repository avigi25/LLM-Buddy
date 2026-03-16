"""
Flask REST API server for LLM Buddy.

Provides HTTP endpoints for recording prompts from browser extensions
and other external tools.
"""

import datetime
import logging
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from llm_buddy.core.database import PromptDatabase, PromptRecord
from llm_buddy.paths import get_logs_dir

_LOG_DIR = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "prompt_server.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize prompt database
prompt_db = PromptDatabase()
prompt_db.load()
logger.info("Prompt database loaded successfully")



@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "prompts_recorded": prompt_db.get_prompts_count(),
    })


@app.route('/record_prompt', methods=['POST'])
def record_prompt():
    """Record a prompt from the browser extension."""
    try:
        data = request.json
        llm_name = data.get('llmName', 'Unknown LLM')
        logger.info("Received prompt from %s", llm_name)
        
        # Get the model name and safely check it
        model_name = data.get('modelName')

        # REPLACE the old check entirely with this new one:
        if model_name and model_name.lower() != llm_name.lower():
            llm_name += f" ({model_name})"

        # Build description
        description = f"Prompt from {llm_name}"            

        if data.get('pageTitle'):
            description += f" - {data['pageTitle']}"

        # Build metadata from extension data
        attachments = data.get('attachments')
        parent_message_id = data.get('parentMessageId')
        messages_count = data.get('messagesCount')
        metadata = {}
        if attachments:
            metadata["attachments"] = attachments
            description += f" [{len(attachments)} attachment(s)]"
        if parent_message_id:
            metadata["parent_message_id"] = parent_message_id
        if messages_count is not None:
            metadata["messages_count"] = messages_count
        metadata = metadata or None

        # Record to unified database
        prompt_id = prompt_db.add_prompt(
            prompt_text=data.get('promptText', ''),
            llm_name=llm_name,
            source="Browser Extension",
            model_name=data.get('modelName'),
            description=description,
            url=data.get('url'),
            conversation_id=data.get('conversationId'),
            metadata=metadata,
        )

        logger.info("Prompt saved to database: %s", description)

        return jsonify({
            "success": True,
            "message": "Prompt recorded successfully",
            "prompt_id": prompt_id,
        })

    except Exception as e:
        logger.error("Error recording prompt: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/prompts', methods=['GET'])
def get_prompts():
    """Retrieve recorded prompts."""
    try:
        prompt_db.load()
        prompts = [
            {
                "id": p.id,
                "timestamp": p.timestamp.isoformat(),
                "llm_used": p.llm_used,
                "description": p.description,
                "prompt_text": p.prompt_text,
                "response_text": getattr(p, "response_text", ""),
                "associated_files": p.associated_files,
                "source": p.source,
            }
            for p in prompt_db.prompts
        ]
        return jsonify({"success": True, "prompts": prompts})
    except Exception as e:
        logger.error("Error retrieving prompts: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/update_response', methods=['POST'])
def update_response():
    """Update the response text for a previously recorded prompt."""
    try:
        data = request.json
        prompt_id = data.get('prompt_id')
        response_text = data.get('response_text', '')

        if not prompt_id:
            return jsonify({
                "success": False,
                "error": "Missing prompt_id",
            }), 400

        if not response_text:
            return jsonify({
                "success": False,
                "error": "Missing response_text",
            }), 400

        success = prompt_db.update_response(prompt_id, response_text)

        if success:
            logger.info("Updated response for prompt %s (%d chars)",
                        prompt_id, len(response_text))
            return jsonify({
                "success": True,
                "message": f"Response updated for prompt {prompt_id}",
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Prompt {prompt_id} not found",
            }), 404

    except Exception as e:
        logger.error("Error updating response: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/update_conversation_id', methods=['POST'])
def update_conversation_id():
    """Update the conversation_id for a previously recorded prompt.

    Used when the first message in a ChatGPT conversation is initially
    recorded with a fallback conversation_id (e.g. "chatgpt.com/") and
    the real UUID becomes available after the response.
    """
    try:
        data = request.json
        prompt_id = data.get('prompt_id')
        conversation_id = data.get('conversation_id')

        if not prompt_id or not conversation_id:
            return jsonify({
                "success": False,
                "error": "Missing prompt_id or conversation_id",
            }), 400

        success = prompt_db.update_conversation_id(prompt_id, conversation_id)

        if success:
            logger.info("Updated conversation_id for prompt %s → %s",
                        prompt_id, conversation_id)
            return jsonify({
                "success": True,
                "message": f"conversation_id updated for prompt {prompt_id}",
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Prompt {prompt_id} not found",
            }), 404

    except Exception as e:
        logger.error("Error updating conversation_id: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/associate_prompt', methods=['POST'])
def associate_prompt():
    """Associate a prompt with a file."""
    try:
        data = request.json
        prompt_id = data.get('prompt_id')
        file_path = data.get('file_path')

        if not prompt_id or not file_path:
            return jsonify({
                "success": False,
                "error": "Missing prompt_id or file_path",
            }), 400

        success = prompt_db.associate_files_with_prompt(
            prompt_id, [file_path])

        if success:
            logger.info("Associated file %s with prompt %s",
                        file_path, prompt_id)
            return jsonify({
                "success": True,
                "message": f"File {file_path} associated with prompt "
                           f"{prompt_id}",
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Prompt {prompt_id} not found",
            }), 404

    except Exception as e:
        logger.error("Error associating prompt: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def run(host='127.0.0.1', port=5000, debug=False):
    """Run the Flask API server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    run(port=port, debug=False)
