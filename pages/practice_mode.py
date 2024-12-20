import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF
import re
import time
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

class RateLimiter:
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.interval = 60 / calls_per_minute
        self.last_call = 0
        self.cache = {}

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

# Create a rate limiter instance
rate_limiter = RateLimiter(calls_per_minute=3)  # Reduced to 3 calls per minute

def extract_text_from_pdf(file):
    """Extracts text from a PDF file-like object uploaded via Streamlit."""
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()

    # Print the extracted text to debug
    print("Extracted Text: ", text[:1000])  # Only print the first 1000 characters for debugging
    return text

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
@rate_limiter
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
        error_msg = str(e)
        if "429" in error_msg:
            st.warning("Rate limit reached. Please wait a moment before trying again...")
            time.sleep(5)  # Add a delay before retrying
            return "Please wait a moment before analyzing the resume."
        st.error(f"An error occurred: {error_msg}")
        return "Could not analyze resume at this time. Please try again."

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
@rate_limiter
def analyze_job_description(job_description_text):
    """Analyzes the job description using AI with 5Ws and 1H approach and adds company background."""
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

    # Debugging: print the prompt to ensure it's being created correctly
    print("Job Description Analysis Prompt: ", prompt[:1000])
    
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=2000,
            temperature=0.5,
        )
    )
    return response.text.strip()

def extract_keywords(text):
    """提取文本中的关键词（使用简单的词频分析或正则表达式）"""
    keywords = re.findall(r'\b\w+\b', text.lower())
    return keywords

def generate_interview_question(job_description_text, resume_text):
    """Generate an interview question based on job description and resume"""
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

# ====Response to User Answer====
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
        error_message = f"An error occurred: {str(e)}"
        if "429" in str(e):
            error_message = "Rate limit exceeded. Please wait a moment before trying again."
        return error_message

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

def main():
    st.set_page_config(
        page_title="Practice Mode",
        page_icon="🤖",
        layout="wide"
    )
    set_theme()
    
    # Add sidebar content
    with st.sidebar:
        st.header("📝 About This App")
        st.markdown("""  
            **Interviewer ChatBot AI**  
            This AI assistant helps you practice interview questions.  
            - Simulates HR interview scenarios  
            - Provides feedback and suggestions  
            - Supports continuous back-and-forth practice
        """)
        
        # Add mode switcher
        st.markdown("---")
        st.subheader("Application Mode")
        
        # Add mode selection
        mode = st.radio(
            "Select Mode",
            ["Practice Mode", "Interviewer Mode"],
            index=0,
            key="mode_selection"
        )
        
        if mode == "Interviewer Mode":
            st.switch_page("interviewer_mode.py")
        
        # Clear chat button with consistent styling
        if st.button("Clear Chat", type="secondary", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": "Ask me anything to start your interview practice!"}
            ]
            st.session_state.current_question = None
            st.session_state.asked_questions = set()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Ask me anything to start your interview practice!"}]

    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    if "asked_questions" not in st.session_state:
        st.session_state.asked_questions = set()

    # Resume and Job Description Uploads
    resume_file = st.file_uploader("Upload Your Resume (PDF)", type="pdf")
    job_description_file = st.file_uploader("Upload Job Description (PDF)", type="pdf")

    resume_text = ""
    job_description_text = ""

    if resume_file:
        resume_text = extract_text_from_pdf(resume_file)
        st.success("Resume uploaded and extracted successfully!")

    if job_description_file:
        job_description_text = extract_text_from_pdf(job_description_file)
        st.success("Job description uploaded and extracted successfully!")

    # Print the extracted text to verify
    print("Job Description Text: ", job_description_text[:1000])  # Debug output

    # Ensure both files are uploaded
    if not resume_file or not job_description_file:
        st.warning("Please upload both your resume and job description.")
        return

    # === Resume Analysis ===
    if resume_text:
        st.subheader("Resume Analysis")
        with st.spinner("Analyzing resume..."):
            try:
                resume_feedback = analyze_resume(resume_text, job_description_text)
                if not resume_feedback.startswith("Please wait"):
                    st.markdown(resume_feedback)
            except Exception as e:
                st.error("Failed to analyze resume. Please try again in a moment.")
                print(f"Error analyzing resume: {str(e)}")

    # === Job Description Analysis ===
    if job_description_text:
        st.subheader("Job Description Analysis")
        with st.spinner("Analyzing job description..."):
            try:
                jd_feedback = analyze_job_description(job_description_text)
                if not jd_feedback.startswith("Please wait"):
                    st.markdown(jd_feedback)
            except Exception as e:
                st.error("Failed to analyze job description. Please try again in a moment.")
                print(f"Error analyzing job description: {str(e)}")

    # Generate an initial interview question if it's the first round
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
        try:
            context = st.session_state.messages

            # Generate feedback for the user's response
            feedback = analyze_answer(query, context)
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.messages.append({"role": "assistant", "content": feedback})

            with st.chat_message("assistant"):
                st.markdown(feedback)

            # Only generate new question if previous response was successful
            if "error" not in feedback.lower():
                question = generate_interview_question(job_description_text, resume_text)
                st.session_state.current_question = question
                st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})

                with st.chat_message("assistant"):
                    st.markdown(st.session_state.current_question)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    # User input handling
    query = st.chat_input("Your response here...")

    if query:
        with st.chat_message("user"):
            st.markdown(query)
        llm_function(query)

if __name__ == "__main__":
    main()