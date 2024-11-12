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
    """extract keywords from text"""
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

        if st.button("Reset Interview", type="primary"):
            reset_all_states()
            # Initialize new chat
            st.session_state.messages = [
                {"role": "assistant", "content": "Let's start a new interview session!"}
            ]
            st.rerun()

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

    # File uploaders
    resume_file = st.file_uploader("Upload Your Resume (PDF)", type="pdf", key="resume_uploader")
    job_description_file = st.file_uploader("Upload Job Description (PDF)", type="pdf", key="jd_uploader")

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
        
        # Generate feedback for the user's response
        feedback = analyze_answer(query, context)
        st.session_state.messages.append({"role": "user", "content": query})
        st.session_state.messages.append({"role": "assistant", "content": feedback})
        
        # Store the response
        st.session_state.user_responses.append({
            "question": st.session_state.current_question,
            "answer": query,
            "feedback": feedback
        })
        
        st.session_state.questions_asked += 1
        
        with st.chat_message("assistant"):
            st.markdown(feedback)
        
        # Check if we've reached the question limit
        if st.session_state.questions_asked >= 2:
            # Prepare responses for final analysis
            interview_summary = "\n\n".join([
                f"Question {i+1}: {resp['question']}\nAnswer: {resp['answer']}\nFeedback: {resp['feedback']}"
                for i, resp in enumerate(st.session_state.user_responses)
            ])
            
            # Generate final analysis
            final_analysis = analyze_interview_performance(interview_summary)
            st.session_state.messages.append({"role": "assistant", "content": "Interview Complete!\n\n" + final_analysis})
            st.session_state.interview_completed = True  # Mark interview as completed
            
            with st.chat_message("assistant"):
                st.markdown("Interview Complete!\n\n" + final_analysis)
                st.markdown("---\n**The interview session has ended. Please click 'Reset Interview' to start a new session.**")
        else:
            # Generate next question
            question = generate_interview_question(job_description_text, resume_text)
            st.session_state.current_question = question
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})
            
            with st.chat_message("assistant"):
                st.markdown(st.session_state.current_question)

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