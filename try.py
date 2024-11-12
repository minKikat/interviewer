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
    return text

def analyze_resume(resume_text, job_description=None):
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
    return response.text.strip()

def extract_keywords(text):
    """Extract keywords from text using simple word frequency analysis or regular expressions"""
    keywords = re.findall(r'\b\w+\b', text.lower())
    return keywords

def generate_interview_question(job_description_text, resume_text):
    prompt = f"""
    You are an experienced HR interviewer. Generate a concise and relevant interview question based on the following job description and candidate's resume:
    
    Job Description: {job_description_text}
    Candidate Resume: {resume_text}

    Ensure the question targets the candidate's skills or experience as mentioned in the job description. The interview question should be simple to complex.
    The interview Generated Interview Question should not be too long. 
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

# Marking Function
def mark_answer(answer):
    """Mark the user's answer on a scale of 1 to 5"""
    # Simple marking logic for demo purposes
    # You can customize this to be more complex if needed
    if len(answer.split()) < 10:
        return 2  # Short answer, give a low score
    elif len(answer.split()) < 30:
        return 3  # Medium-length answer
    elif len(answer.split()) < 50:
        return 4  # Good answer
    else:
        return 5  # Excellent answer

# ====Response to User Answer====
def analyze_answer(query, context):
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
            st.session_state.answer_count = 0  # Reset the number of answers
            st.session_state.user_answers = []  # Track user answers

    # Initialize session state if not already initialized
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Ask me anything to start your interview practice!"}]

    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    if "asked_questions" not in st.session_state:
        st.session_state.asked_questions = set()

    if "answer_count" not in st.session_state:
        st.session_state.answer_count = 0  # Track how many answers have been provided

    if "user_answers" not in st.session_state:
        st.session_state.user_answers = []  # Store all user answers

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
    if resume_text and job_description_text and st.session_state.answer_count < 3:
        question = generate_interview_question(job_description_text, resume_text)
        st.session_state.current_question = question
        st.session_state.messages.append({"role": "assistant", "content": question})

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input for chat simulation
    query = st.chat_input("Your response here...")  # User input handling with chat_input

    if query:
        with st.chat_message("user"):
            st.markdown(query)

        # Call the analyze_answer function to process the user's response
        response = analyze_answer(query, st.session_state.messages)  # Analyze the answer
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Store the user's answer
        st.session_state.user_answers.append(query)

        # Scoring and moving to next question
        score = mark_answer(query)  # Calculate the score
        st.session_state.messages.append({"role": "assistant", "content": f"Your score for this answer is: {score}"})

        # Increment the count and check if we can move to the next question
        st.session_state.answer_count += 1

        # Display the score after all answers (After 3 answers)
        if st.session_state.answer_count >= 3:
            total_score = sum([mark_answer(answer) for answer in st.session_state.user_answers])
            average_score = total_score / len(st.session_state.user_answers)
            st.session_state.messages.append({"role": "assistant", "content": f"Your total score is: {total_score}/{len(st.session_state.user_answers) * 5} (Average score: {average_score:.2f})"})
            
        # Generate the next question once the previous answer is processed
        if st.session_state.answer_count < 3:
            question = generate_interview_question(job_description_text, resume_text)
            st.session_state.current_question = question
            st.session_state.messages.append({"role": "assistant", "content": question})
