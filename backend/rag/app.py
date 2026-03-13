from flask import *
from flask_cors import CORS, cross_origin
from playhouse.shortcuts import model_to_dict
from models import *
from directory import *
from cache import *
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.chroma import Chroma
from transformers import pipeline
import torch
import json
import jwt
import  re
from waitress import serve
import requests
from dotenv import load_dotenv
import os
from google import genai
import logging

# Import multi-turn chat blueprint
from chat_endpoints import chat_bp, embeddings, vectordb, gemini_client


load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

current_device = "cpu"
if torch.cuda.is_available():
    current_device="cuda"
# embeddings = HuggingFaceEmbeddings(model_name=ST_MODEL_PATH, model_kwargs={"device": current_device})
# vectordb = Chroma(embedding_function=embeddings,
#                   persist_directory=TOPIC_DB_PATH)

# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# gemini_client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# Register multi-turn chat blueprint
app.register_blueprint(chat_bp)

@app.route('/api/v1/question', methods=['GET'])
def get_question(email=None):
    try:
        token = request.headers.get('Authorization')

        if token and token.startswith('Bearer '):
            token = token[7:]
            
        decoded = jwt.decode(token, ACCESS_TOKEN_KEY, algorithms=['HS256'])
        email = decoded['email']
    except:
        return {
            "status": "error",
            "response": "Need authentication",
        }, 401

    if email:
        query = QuestionModel.select().where(email == QuestionModel.email).dicts()
        res = []
        for row in query:
            answer = []
            query1 = Reference.select().where(row['id'] == Reference.question_id).dicts()
            for r in query1: 
                answer.append({"mapc": r['mapc'], "noidung": r['noidung'], "ten": r['ten']})
            res.append({
                "id": row['id'],
                "email": row['email'],
                "question": row['question'],
                "updatedAt": row['updatedAt'].strftime("%m/%d/%Y"),
                "response": row['response'],
                "answer": answer
            })
        return res, 201
    
@app.route('/api/v1/question', methods=['POST'])
def add_question():
    try:
        token = request.headers.get('Authorization')

        if token and token.startswith('Bearer '):
            token = token[7:]
        data = request.get_json()
        decoded = jwt.decode(token, ACCESS_TOKEN_KEY, algorithms=['HS256'])

        email = decoded['email']
    except:
        return {
            "status": "error",
            "response": "Need authentication",
        }, 401

    try:
        question = data["question"]
    except:
        return {
            "status": "error",
            "response": "No question in payload",
        }, 400
    
    if not question:
        return {
            "status": "error",
            "response": "Question can not be empty",
        }, 400

    if (redisClient.get(question)): 
        return json.loads(redisClient.get(question).decode('utf-8')), 200
    
    output = vectordb.similarity_search(question, k=2)
    context = ""
    citation = []
    for doc in output:
        result_string = doc.page_content
        index = result_string.find("noidung: ")
        if index != -1:
            result_string = result_string[index + len("noidung: "):].strip()
        result_string = result_string.replace("\n", " ")
        result_string = re.sub(r"\s+", r" ", result_string)
        context += f"{result_string} "

        citation.append({
            "mapc": doc.metadata.get("mapc", doc.metadata.get("dieu_title", "")),
            "_link": doc.metadata.get("_link", ""),
            "chude_id": doc.metadata.get("chude_id", ""),
            "demuc_id": doc.metadata.get("demuc_id", ""),
            "ten": doc.metadata.get("ten", doc.metadata.get("demuc_name", "")),
            "noidung": result_string
        })
    
    context = context.strip()
    if not context:
        return {
            "status": "error",
            "response": "Error while retrieving context from DB",
        }, 500


    inputs = f"Dựa vào văn bản sau đây:\n{context}\nHãy trả lời câu hỏi: {question}"
    try:
        gemini_response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=inputs,
        )
        response = gemini_response.text
    except Exception as e:
        return {
            "status": "error",
            "response": f"Gemini API error: {str(e)}",
        }, 500
    if not response:
        return {
            "status": "error",
            "response": "Empty response from AI model",
        }, 500


    # response = pipeline(question=question, context=context)["answer"].strip()

    query = QuestionModel.create(**{"email": email, "question": question ,"response": response})
    for c in citation: 
        Reference.create(**{'question_id': query.id, 'mapc': c['mapc'], 'noidung': c['noidung'], 'ten': c['ten']})
    res = {
        "status": "success",
        "question": question,
        "citation": citation,
        "response": response,
    }
    redisClient.set(question, json.dumps(res))
    return res, 200

@app.route('/api/v1/question-with-context', methods=['POST'])
def add_question_with_context():
    try: 
        token = request.headers.get('Authorization')

        if token and token.startswith('Bearer '):
            token = token[7:]
        data = request.get_json()
        decoded = jwt.decode(token, ACCESS_TOKEN_KEY, algorithms=['HS256'])

        email = decoded['email']
    except: 
         return {
            "status": "error",
            "response": "Need authentication",
        }, 401
         
    try:
        question = data["question"]
        context = data["context"]
    except:
        return {
            "status": "error",
            "response": "Question or Context not found in the payload",
        }, 400
    
    if not question:
        return {
            "status": "error",
            "response": "Question can not be empty",
        }, 400
    if not context:
        return {
            "status": "error",
            "response": "Context can not be empty",
        }, 400
    if (redisClient.get(question)): 
        return json.loads(redisClient.get(question).decode('utf-8')), 200
    
    output = vectordb.similarity_search(question, k=2)

    
    citation = []
    for doc in output:
        result_string = doc.page_content
        index = result_string.find("noidung: ")
        if index != -1:
            result_string = result_string[index + len("noidung: "):].strip()
        result_string = result_string.replace("\n", " ")
        result_string = re.sub(r"\s+", r" ", result_string)

        citation.append({
            "mapc": doc.metadata.get("mapc", doc.metadata.get("dieu_title", "")),
            "_link": doc.metadata.get("_link", ""),
            "chude_id": doc.metadata.get("chude_id", ""),
            "demuc_id": doc.metadata.get("demuc_id", ""),
            "ten": doc.metadata.get("ten", doc.metadata.get("demuc_name", "")),
            "noidung": result_string
        })
    
    


    inputs = f"Dựa vào văn bản sau đây:\n{context}\nHãy trả lời câu hỏi: {question}"
    try:
        gemini_response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=inputs,
        )
        response = gemini_response.text
    except Exception as e:
        return {
            "status": "error",
            "response": f"Gemini API error: {str(e)}",
        }, 500
    if not response:
        return {
            "status": "error",
            "response": "Empty response from AI model",
        }, 500


    # response = pipeline(question=question, context=context)["answer"].strip()

    query = QuestionModel.create(**{"email": email, "question": question ,"response": response})
    for c in citation: 
        Reference.create(**{'question_id': query.id, 'mapc': c['mapc'], 'noidung': c['noidung'], 'ten': c['ten']})
    res = {
        "status": "success",
        "question": question,
        "citation": citation,
        "response": response,
    }
    redisClient.set(question, json.dumps(res))
    return res, 200


@app.route('/api/v1/question/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    data = request.get_json()
    QuestionModel.update(**data).where(QuestionModel.id == question_id).execute()
    return '', 204

@app.route('/api/v1/question/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    QuestionModel.delete().where(QuestionModel.id == question_id).execute()
    return '', 204


@app.route('/api/v1/validate-query', methods=['POST'])
def validate_query():
    """
    Validate user query để xác định loại câu hỏi
    
    Request body:
    {
        "question": "Câu hỏi của user"
    }
    
    Returns:
    {
        "status": "success",
        "type": "chitchat" | "legal_unclear" | "legal_clear",
        "message": "Optional clarification question if legal_unclear",
        "keywords": []
    }
    """
    try:
        data = request.get_json()
        if not data:
            return {
                "status": "error",
                "message": "Request body is required"
            }, 400
        
        question = data.get('question', '').strip()
        if not question:
            return {
                "status": "error",
                "message": "Question cannot be empty"
            }, 400
        
        # Call LLM to analyze query
        validation_prompt = f"""
Phân tích câu hỏi sau và xác định loại:
1. "chitchat" - Nếu là nội dung không liên quan đến pháp luật (chào hỏi, câu hỏi sinh hoạt, v.v.)
2. "legal_unclear" - Nếu liên quan đến pháp luật nhưng chưa rõ ràng, cần clarification
3. "legal_clear" - Nếu là câu hỏi pháp luật rõ ràng, cụ thể

Câu hỏi: "{question}"

Trả lời theo format JSON (không có markdown):
{{
    "type": "chitchat|legal_unclear|legal_clear",
    "clarification_question": "Nếu legal_unclear, đặt câu hỏi để làm rõ thêm",
    "keywords": ["keyword1", "keyword2"]
}}
"""
        
        gemini_response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=validation_prompt,
        )
        
        response_text = gemini_response.text.strip()
        
        # Try to parse JSON from response
        import json
        try:
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            parsed = json.loads(response_text)
            
            return {
                "status": "success",
                "type": parsed.get("type", "legal_unclear"),
                "message": parsed.get("clarification_question", ""),
                "keywords": parsed.get("keywords", [])
            }, 200
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {response_text}")
            logger.error(f"GEMINI KEY: {GEMINI_API_KEY}")
            # Fallback to legal_unclear if parsing fails
            return {
                "status": "success",
                "type": "legal_unclear",
                "message": "Vui lòng cung cấp thêm thông tin chi tiết về câu hỏi của bạn.",
                "keywords": []
            }, 200
    
    except Exception as e:
        logger.error(f"Error validating query: {str(e)}")
        logger.error(f"GEMINI KEY: {GEMINI_API_KEY}")
        # Return consistent response structure even on error
        return {
            "status": "success",
            "type": "legal_unclear",
            "message": "Xảy ra lỗi khi xác định loại câu hỏi. Vui lòng cung cấp thêm thông tin chi tiết.",
            "keywords": []
        }, 200


if __name__ == '__main__':
    logger.info('QNA server is starting...')
    logger.info('Available endpoints:')
    logger.info('  Legacy v1 endpoints: /api/v1/question')
    logger.info('  Multi-turn v2 endpoints: /api/v2/chat/*')
    serve(app, host='0.0.0.0', port=5001, threads=4)