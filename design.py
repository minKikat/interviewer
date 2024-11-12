import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF
import re

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def extract_text_from_pdf(file):
    """Extracts text from a PDF file-like object uploaded via Streamlit."""
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()

    # Print the extracted text to debug
    print("Extracted Text: ", text[:1000])  # Only print the first 1000 characters for debugging
    return text

def analyze_resume(resume_text, job_description=None):
    """Analyzes resume content with AI, optionally including job description."""
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

def main():
    st.set_page_config(page_title="Interviewer ChatBot AI", page_icon="🤖", layout="wide")
    st.markdown(
    """
    <style>
        /* General Background */
        .stApp {
            background-color: var(--background-color, #f0f4c3);
        }

        /* Chat Message Background */
        .stChatMessage {
            background-color: var(--chat-background-color, #fff3e0);
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            color: var(--text-color, #004d40);
        }

        /* Input Field */
        .stTextInput {
            border: 2px solid #ffab91;
            border-radius: 8px;
            padding: 8px;
            color: var(--text-color, #004d40);
        }

        /* Title Text */
        .stMarkdown h1 {
            color: var(--title-color, #00796b);
        }

        /* Chat Text */
        .stMarkdown p {
            color: var(--text-color, #004d40);
        }

        /* Dark Mode Styling */
        @media (prefers-color-scheme: dark) {
            .stApp {
                --background-color: #1e1e1e;
                --chat-background-color: #2e2e2e;
                --text-color: #e0e0e0;
                --title-color: #80cbc4;
            }
        }
    </style>
    """,
    unsafe_allow_html=True
)
    st.title("Interviewer ChatBot AI")

    # === Sidebar ===
    with st.sidebar:
        st.header("📝 About This App")
        st.markdown("""  
            **Interviewer ChatBot AI**  
            This AI assistant helps you practice interview questions.  
            - Simulates HR interview scenarios  
            - Provides feedback and suggestions  
            - Supports continuous back-and-forth practice
        """)

        if st.button("Clear Chat"):
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
        context = st.session_state.messages

        # Generate feedback for the user's response
        feedback = analyze_answer(query, context)
        st.session_state.messages.append({"role": "user", "content": query})
        st.session_state.messages.append({"role": "assistant", "content": feedback})

        with st.chat_message("assistant"):
            st.markdown(feedback)

        # Generate a new interview question after feedback
        question = generate_interview_question(job_description_text, resume_text)
        st.session_state.current_question = question
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})

        with st.chat_message("assistant"):
            st.markdown(st.session_state.current_question)

    # User input handling
    query = st.chat_input("Your response here...")

    if query:
        with st.chat_message("user"):
            st.markdown(query)
        llm_function(query)

if __name__ == "__main__":
    main()