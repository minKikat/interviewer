import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def generate_content(query, context, is_question=False):
    # Check if there are at least two messages in the context to prevent IndexError
    if len(context) >= 2 and isinstance(context[-2], dict) and 'content' in context[-2]:
        question_content = f"* **Question:** {context[-2]['content']}\n"
    else:
        question_content = ""

    # Modify the system message based on whether we need a question or feedback
    if is_question:
        system_content = (
            f"You are an experienced HR interviewer. Please generate a new interview question based on the job description. "
            f"The interview question should not be too long."
        )
    else:
        system_content = (
            "You are an experienced HR interviewer. Your goal is to provide constructive feedback to help the candidate improve their interview skills.\n\n"
            f"{question_content}* **User's Response:** {query}\n\n"
            "Evaluate the user's response based on relevance, clarity, technical accuracy, communication skills, and problem-solving skills. "
            "If the response is irrelevant, unclear, or nonsensical acknowledge that the response doesn't address the question and encourage the user to focus on the relevant aspects. "
            "Provide tips or ideas on how to answer the question effectively, such as asking for specific examples or encouraging the use of a structured response like the STAR method (Situation, Task, Action, Result). "
            "If the response is incorrect, provide a correct or theoretical answer and explain why the user's response was lacking or incorrect. "
            "If the response is correct, suggest ways to improve the answer by elaborating on key points, adding more examples, or offering alternative ways to present the information more clearly."
        )

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        system_content,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=1000,
            temperature=0.5,
        )
    )
    return response.text.strip()

def extract_text_from_pdf(file):
    """Extracts text from a PDF file-like object uploaded via Streamlit."""
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
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
    
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=2000,
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

    # Ensure both files are uploaded
    if not resume_file or not job_description_file:
        st.warning("Please upload both your resume and job description.")
        return

    # Resume Analysis and Feedback
    if resume_text:
        st.subheader("Resume Analysis")
        resume_feedback = analyze_resume(resume_text, job_description_text)
        st.markdown(resume_feedback)

    # Job Description Analysis and Question Generation
    if job_description_text:
        st.subheader("Job Description Analysis")
        jd_feedback = analyze_job_description(job_description_text)
        st.markdown(jd_feedback)
        
        # Generate a question based on the job description
        question = generate_content("", jd_feedback, is_question=True)
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
        feedback = generate_content(query, context)
        st.session_state.messages.append({"role": "user", "content": query})
        st.session_state.messages.append({"role": "assistant", "content": feedback})

        with st.chat_message("assistant"):
            st.markdown(feedback)

        # Clear current question to prompt generation of a new one
        st.session_state.current_question = None

        # Generate a new question based on the job description
        if not st.session_state.current_question:
            question = generate_content(query, context, is_question=True)
            st.session_state.current_question = question
            st.session_state.asked_questions.add(question)

            # Display the new question
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
