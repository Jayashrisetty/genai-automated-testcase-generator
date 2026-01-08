"""
AI-Driven Test Case Generator - Main Cloud Run Service
Automatically generates unit, edge-case, and negative test cases using Gemini AI
"""

from flask import Flask, request, jsonify
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel
import json
import os
from datetime import datetime
from code_analyzer import CodeAnalyzer
from test_generator import TestGenerator

app = Flask(__name__)

# Initialize Vertex AI
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'your-project-id')
LOCATION = os.getenv('GCP_LOCATION', 'us-central1')
BUCKET_NAME = os.getenv('GCS_BUCKET', 'ai-test-generator-bucket')

vertexai.init(project=PROJECT_ID, location=LOCATION)

# Initialize components
storage_client = storage.Client()
code_analyzer = CodeAnalyzer()
test_generator = TestGenerator(project_id=PROJECT_ID, location=LOCATION)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'ai-test-generator'}), 200


@app.route('/generate-tests', methods=['POST'])
def generate_tests():
    """
    Main endpoint to generate test cases
    
    Request body:
    {
        "source_code": "string (optional if using gcs_path)",
        "gcs_path": "gs://bucket/path/to/file.py (optional if using source_code)",
        "language": "python|java|javascript",
        "test_types": ["unit", "edge", "negative"],
        "framework": "pytest|unittest|jest|junit"
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Get source code (either directly or from GCS)
        source_code = data.get('source_code')
        gcs_path = data.get('gcs_path')
        
        if not source_code and not gcs_path:
            return jsonify({'error': 'Either source_code or gcs_path is required'}), 400
        
        if gcs_path:
            source_code = download_from_gcs(gcs_path)
        
        language = data.get('language', 'python')
        test_types = data.get('test_types', ['unit', 'edge', 'negative'])
        framework = data.get('framework', 'pytest')
        
        # Step 1: Analyze source code
        analysis_result = code_analyzer.analyze(source_code, language)
        
        if not analysis_result['success']:
            return jsonify({
                'error': 'Code analysis failed',
                'details': analysis_result.get('error')
            }), 400
        
        # Step 2: Generate test cases using Gemini
        generated_tests = test_generator.generate(
            source_code=source_code,
            analysis=analysis_result['analysis'],
            language=language,
            test_types=test_types,
            framework=framework
        )
        
        # Step 3: Save results to GCS
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"generated_tests/{timestamp}_tests.py"
        gcs_url = upload_to_gcs(generated_tests['test_code'], output_path)
        
        # Prepare response
        response = {
            'success': True,
            'generated_tests': generated_tests['test_code'],
            'gcs_path': gcs_url,
            'metadata': {
                'functions_analyzed': len(analysis_result['analysis']['functions']),
                'test_cases_generated': generated_tests['test_count'],
                'test_types': test_types,
                'framework': framework,
                'timestamp': timestamp
            },
            'analysis_summary': analysis_result['analysis']['summary']
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/analyze-code', methods=['POST'])
def analyze_code():
    """
    Endpoint to only analyze code without generating tests
    """
    try:
        data = request.get_json()
        source_code = data.get('source_code')
        gcs_path = data.get('gcs_path')
        
        if gcs_path:
            source_code = download_from_gcs(gcs_path)
        
        if not source_code:
            return jsonify({'error': 'source_code or gcs_path is required'}), 400
        
        language = data.get('language', 'python')
        
        analysis_result = code_analyzer.analyze(source_code, language)
        
        return jsonify(analysis_result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def download_from_gcs(gcs_path: str) -> str:
    """Download file from Google Cloud Storage"""
    if not gcs_path.startswith('gs://'):
        raise ValueError('GCS path must start with gs://')
    
    path_parts = gcs_path[5:].split('/', 1)
    bucket_name = path_parts[0]
    blob_name = path_parts[1]
    
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    return blob.download_as_text()


def upload_to_gcs(content: str, destination_path: str) -> str:
    """Upload content to Google Cloud Storage"""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_path)
    
    blob.upload_from_string(content)
    
    return f"gs://{BUCKET_NAME}/{destination_path}"


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
