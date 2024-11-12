import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF
import re
from streamlit.components.v1 import html
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime, timedelta
import hashlib
import json
from functools import wraps

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Define all your functions here
def extract_text_from_pdf(file):
    """Extracts text from a PDF file-like object uploaded via Streamlit."""
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()

    # Print the extracted text to debug
    print("Extracted Text: ", text[:1000])  # Only print the first 1000 characters for debugging
    return text

class RateLimiter:
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.interval = 60 / calls_per_minute
        self.last_call = 0

    def can_make_call(self):
        """Check if a call can be made based on the rate limit"""
        now = time.time()
        time_since_last_call = now - self.last_call
        return time_since_last_call >= self.interval

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            time_since_last_call = now - self.last_call
            if time_since_last_call < self.interval:
                time.sleep(self.interval - time_since_last_call)
            self.last_call = time.time()
            return func(*args, **kwargs)
        return wrapper

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
@RateLimiter(calls_per_minute=5)
def analyze_resume(resume_text, job_description=None):
    """Analyzes resume content with AI, optionally including job description."""
    try:
        prompt = f"""
        Analyze the following resume content:
        {resume_text}
        
        Evaluate the resume based on its relevance to the job description. Focus on technical skills, relevant experience, and qualifications.
        """
        
        if job_description:
            prompt += f"\nAdditionally, evaluate it in the context of the following job description:\n{job_description}"

        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=2000,
                temperature=0.5,
            )
        )
        return response.text.strip()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return "Could not analyze resume at this time. Please try again."

# Add a caching mechanism
class SimpleCache:
    def __init__(self):
        self.cache = {}
    
    def get_cache_key(self, func_name, *args):
        # Create a unique key based on function name and arguments
        key_parts = [func_name] + [str(arg) for arg in args]
        key_string = json.dumps(key_parts, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, func_name, *args):
        key = self.get_cache_key(func_name, *args)
        if key in self.cache:
            return self.cache[key]
        return None
    
    def set(self, func_name, value, *args):
        key = self.get_cache_key(func_name, *args)
        self.cache[key] = value

# Create global instances
cache = SimpleCache()
rate_limiter = RateLimiter(calls_per_minute=5)  # Reduced to 5 calls per minute

# Update the analyze_job_description function with caching and rate limiting
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=10),
    reraise=True
)
@RateLimiter(calls_per_minute=5)
def analyze_job_description(job_description_text):
    """Analyzes the job description using AI with 5Ws and 1H approach."""
    # Check cache first
    cached_result = cache.get('analyze_job_description', job_description_text)
    if cached_result:
        return cached_result

    # Check rate limit
    if not rate_limiter.can_make_call():
        st.warning("Rate limit reached. Please wait a moment...")
        time.sleep(10)  # Force wait for 10 seconds
        return "Please wait a moment before analyzing the job description."

    try:
        prompt = f"""
        Analyze the following job description using the 5Ws and 1H framework:
        - Who is the ideal candidate for this role?
        - What are the key responsibilities and qualifications?
        - When and where will the role be performed?
        - Why is this role important to the company?
        - How should the candidate approach the tasks or challenges outlined in the description?

        Additionally, if the company name is mentioned, provide a brief background on the company.

        Job description:
        {job_description_text}
        """
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=2000,
                temperature=0.5,
            )
        )
        result = response.text.strip()
        
        # Cache the result
        cache.set('analyze_job_description', result, job_description_text)
        return result
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return "Could not analyze job description at this time. Please try again in a few moments."

def extract_keywords(text):
    """extract keywords from text"""
    keywords = re.findall(r'\b\w+\b', text.lower())
    return keywords

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
@RateLimiter(calls_per_minute=5)
def generate_interview_question(job_description_text, resume_text):
    """Generate an interview question based on job description and resume"""
    try:
        prompt = f"""
        You are an experienced HR interviewer. Generate a concise and relevant interview question based on the following job description and candidate's resume:
        
        Job Description: {job_description_text}
        Candidate Resume: {resume_text}

        Ensure the question targets the candidate's skills or experience as mentioned in the job description. The interview question from simple to complex. 
        The interview Generated Interview Questionuestion should not be too long. 
        """
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=150,
                temperature=0.5,
            )
        )
        return response.text.strip()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return "Could not generate a question at this time. Please try again."

# ====Response to User Answer====
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
@RateLimiter(calls_per_minute=5)
def analyze_answer(query, context):
    """Generate feedback based on user's response to the interview question"""
    try:
        prompt = f"""
        You are an experienced HR interviewer. The user's response to the interview question is below. 
        "Evaluate the user's response based on relevance, clarity, technical accuracy, communication skills, and problem-solving skills. "
        "If the response is irrelevant, unclear, or nonsensical, acknowledge that the response doesn't address the question and encourage the user to focus on the relevant aspects. "
        "Provide tips or example better answer on how to answer the question effectively, such as asking for specific examples or encouraging the use of a structured response. "
        "If the response is incorrect, provide a correct or theoretical answer and explain why the user's response was lacking or incorrect. "
        "If the response is correct, suggest ways to improve the answer by elaborating on key points, adding more examples, or offering alternative ways to present the information more clearly."

        Interview Question: {context[-2]['content']}
        User's Response: {query}
        """

        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=1000,
                temperature=0.5,
            )
        )
        return response.text.strip()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return "I apologize, but I'm currently experiencing high traffic. Please try again in a few moments."

def analyze_interview_performance(responses):
    """Analyzes overall interview performance and provides a summary with score"""
    prompt = f"""
    As an HR interviewer, analyze the following interview responses and provide:
    1. An overall score out of 100
    2. A summary of strengths and weaknesses
    3. Key areas for improvement
    
    Interview Responses:
    {responses}
    
    Format the response as:
    Score: [X]/100
    
    Overall Assessment:
    [Summary paragraph]
    
    Strengths:
    - [Point 1]
    - [Point 2]
    
    Areas for Improvement:
    - [Point 1]
    - [Point 2]
    
    Recommendations:
    - [Point 1]
    - [Point 2]
    """
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=1000,
            temperature=0.5,
        )
    )
    return response.text.strip()

def reset_all_states():
    # List of ALL session state keys to reset, including file uploads
    keys_to_reset = [
        'messages',
        'current_question',
        'asked_questions',
        'questions_asked',
        'user_responses',
        'interview_completed',
        'resume_file',
        'job_description_file',
        'resume_uploader',  # Clear file uploader state
        'jd_uploader'      # Clear file uploader state
    ]
    
    # Reset each key
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

def set_theme():
    """Sets theme CSS with improved visibility for both modes"""
    css = """
    <style>
        /* Dark mode - keeping current styling */
        @media (prefers-color-scheme: dark) {
            .stApp {
                background-color: #0E1117;
            }
            
            .main-header {
                color: #FF6B6B !important;
            }
            
            [data-testid="stSidebar"] {
                background-color: #1E1E2E;
            }
            
            [data-testid="stSidebar"] p {
                color: #FFFFFF !important;
            }
            
            [data-testid="stFileUploader"] {
                background-color: #262736 !important;
            }
            
            [data-testid="stMarkdownContainer"] {
                color: #FFFFFF !important;
            }
            
            .stAlert {
                background-color: rgba(255, 171, 0, 0.1) !important;
                color: #FFB700 !important;
            }
        }

        /* Light mode - enhanced contrast */
        @media (prefers-color-scheme: light) {
            .stApp {
                background-color: #FFFFFF;
            }
            
            .main-header {
                color: #FF6B6B !important;
            }
            
            [data-testid="stSidebar"] {
                background-color: #F0F2F6;
            }
            
            [data-testid="stSidebar"] p {
                color: #000000 !important;
            }
            
            [data-testid="stFileUploader"] {
                background-color: #FFFFFF !important;
            }
            
            [data-testid="stMarkdownContainer"] {
                color: #000000 !important;
            }
            
            .stAlert {
                background-color: #FFF3CD !important;
                color: #664D03 !important;
                border: 1px solid #FFE69C !important;
            }
            
            /* Ensure all text is dark in light mode */
            p, span, label, div {
                color: #000000 !important;
            }
            
            /* File uploader text */
            [data-testid="stFileUploader"] span {
                color: #000000 !important;
            }
            
            /* Limit text color */
            .uploadedFileName {
                color: #000000 !important;
            }
        }

        /* Common styles for both modes */
        .stButton button {
            background-color: #FF6B6B !important;
            color: white !important;
        }
        
        [data-testid="stFileUploader"] button {
            background-color: #4ECDC4 !important;
            color: white !important;
        }
        
        /* Ensure headers are properly styled */
        h1, h2, h3 {
            font-weight: 600 !important;
        }
        
        /* Style file upload containers */
        [data-testid="stFileUploader"] {
            border: 1px solid #4ECDC4 !important;
            border-radius: 8px !important;
            padding: 1rem !important;
        }
        
        /* Style the drag and drop area */
        [data-testid="stFileUploader"] [data-testid="stImageButton"] {
            border: 2px dashed #4ECDC4 !important;
            border-radius: 8px !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Create a global rate limiter
rate_limiter = RateLimiter(calls_per_minute=10)

# Use it in your API calls
def make_api_call():
    if not rate_limiter.can_make_call():
        st.error("Rate limit exceeded. Please wait a moment before trying again.")
        return None
    # Make your API call here

def main():
    st.set_page_config(page_title="Interviewer ChatBot AI (Interviewer Mode)", page_icon="🤖", layout="wide")
    set_theme()
    
    # Add sidebar content
    with st.sidebar:
        st.header("📝 About This App")
        st.markdown("""  
            **Interviewer ChatBot AI**  
            This AI assistant helps you conduct interviews.  
            - Create interview scenarios  
            - Provide feedback to candidates  
            - Manage interview sessions
        """)
        
        # Add mode switcher
        st.markdown("---")
        st.subheader("Application Mode")
        
        # Add mode selection
        mode = st.radio(
            "Select Mode",
            ["Interviewer Mode", "Practice Mode"],
            index=0,  # Default to Interviewer Mode
            key="mode_selection"
        )
        
        if mode == "Practice Mode":
            st.switch_page("pages/practice_mode.py")
        
        # Reset button
        if st.button("Reset Interview", type="secondary", use_container_width=True):
            reset_all_states()
            st.session_state.messages = [
                {"role": "assistant", "content": "Let's start a new interview session!"}
            ]
            st.rerun()

    # Wrap main content in styled containers
    with st.container():
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        
        # File uploaders with improved styling
        col1, col2 = st.columns(2)
        with col1:
            resume_file = st.file_uploader(
                "Upload Your Resume (PDF)",
                type="pdf",
                key="resume_uploader",
                help="Upload your resume in PDF format"
            )
        with col2:
            job_description_file = st.file_uploader(
                "Upload Job Description (PDF)",
                type="pdf",
                key="jd_uploader",
                help="Upload the job description in PDF format"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Ask me anything to start your interview practice!"}]

    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    if "asked_questions" not in st.session_state:
        st.session_state.asked_questions = set()

    if "questions_asked" not in st.session_state:
        st.session_state.questions_asked = 0
    
    if "user_responses" not in st.session_state:
        st.session_state.user_responses = []

    # Add this to session state initialization
    if "interview_completed" not in st.session_state:
        st.session_state.interview_completed = False

    # Store the uploaded files in session state
    if resume_file is not None:
        st.session_state.resume_file = resume_file
    if job_description_file is not None:
        st.session_state.job_description_file = job_description_file

    resume_text = ""
    job_description_text = ""

    # Process uploaded files
    if resume_file:
        resume_text = extract_text_from_pdf(resume_file)
        st.success("Resume uploaded and extracted successfully!")
    elif 'resume_file' in st.session_state:
        # Seek to beginning of file before reading
        st.session_state.resume_file.seek(0)
        resume_text = extract_text_from_pdf(st.session_state.resume_file)

    if job_description_file:
        job_description_text = extract_text_from_pdf(job_description_file)
        st.success("Job description uploaded and extracted successfully!")
    elif 'job_description_file' in st.session_state:
        # Seek to beginning of file before reading
        st.session_state.job_description_file.seek(0)
        job_description_text = extract_text_from_pdf(st.session_state.job_description_file)

    # Print the extracted text to verify
    print("Job Description Text: ", job_description_text[:1000])  # Debug output

    # Ensure both files are uploaded
    if not resume_file or not job_description_file:
        st.warning("Please upload both your resume and job description.")
        return

    # === Resume Analysis ===
    if resume_text:
        st.subheader("Resume Analysis")
        resume_feedback = analyze_resume(resume_text, job_description_text)
        st.markdown(resume_feedback)
    else:
        st.warning("No text found in the resume PDF.")

    # === Job Description Analysis ===
    if job_description_text:
        st.subheader("Job Description Analysis")
        jd_feedback = analyze_job_description(job_description_text)
        st.markdown(jd_feedback)
    else:
        st.warning("No text found in the job description PDF.")

    # Generate initial question if both files are present
    if resume_text and job_description_text and not st.session_state.current_question:
        question = generate_interview_question(job_description_text, resume_text)
        st.session_state.current_question = question
        st.session_state.messages.append({"role": "assistant", "content": question})

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Continuous question handling
    def llm_function(query):
        context = st.session_state.messages
        
        try:
            # Generate feedback for the user's response
            feedback = analyze_answer(query, context)
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.messages.append({"role": "assistant", "content": feedback})
            
            with st.chat_message("assistant"):
                st.markdown(feedback)
            
            # Add a small delay before generating the next question
            time.sleep(2)
            
            # Generate next question
            question = generate_interview_question(job_description_text, resume_text)
            st.session_state.current_question = question
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})
            
            with st.chat_message("assistant"):
                st.markdown(st.session_state.current_question)
        except Exception as e:
            st.error("An error occurred. Please wait a moment and try again.")

    # User input handling
    if not st.session_state.interview_completed:
        query = st.chat_input("Your response here...")
        if query:
            with st.chat_message("user"):
                st.markdown(query)
            llm_function(query)
    else:
        # Display a disabled input box with a message
        st.text_input(
            "Interview completed",
            value="Interview session has ended. Click 'Reset Interview' to start a new session.",
            disabled=True
        )

if __name__ == "__main__":
    main()