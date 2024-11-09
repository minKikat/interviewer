import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def generate_content(query, position, context, is_question=False):
    # Check if there are at least two messages in the context to prevent IndexError
    if len(context) >= 2:
        question_content = f"* **Question:** {context[-2]['content']}\n"
    else:
        question_content = ""

    # Modify the system message based on whether we need a question or feedback
    if is_question:
        system_content = (
            f"You are an experienced HR interviewer specializing in {position} interviews. "
            f"Please generate a new interview question relevant to the position of {position}. The interview question should not too long"
        )
    else:
        system_content = (
        f"You are an experienced HR interviewer specializing in {position} interviews. Your goal is to provide constructive feedback that helps the candidate improve their interview skills.\n\n"
        f"{question_content}"
        f"* **User's Response:** {query}\n\n"
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

def analyze_resume(resume_text, position, job_description=None):
    """Analyzes resume content with AI, optionally including job description."""
    prompt = f"""
    You are an experienced {position} interviewer. Analyze the following resume content:
    {resume_text}
    
    Evaluate the resume based on the relevance for a {position} role. Focus on technical skills, relevant experience, and other qualifications.
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
    """Analyzes the job description using AI."""
    prompt = f"""
    You are an experienced interviewer. Please analyze the following job description:
    {job_description_text}
    
    You need to based on the position and job description to generate the interview questions. Suggest any areas where the candidate might need to improve or focus on.
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

        # Add IT Job Position buttons
        st.subheader("Select IT Job Position")
        job_positions = ["Software Engineer", "Data Scientist", "DevOps Engineer", "Product Manager"]

        for position in job_positions:
            if st.button(position):
                st.session_state.selected_position = position
                st.session_state.messages = [
                    {"role": "assistant", "content": f"Let's start the interview for the {position} position. Tell me about yourself."}
                ]
                st.session_state.asked_questions = set()
                st.session_state.current_question = None

        if st.button("Clear Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Ask me anything to start your interview practice!"}
            ]
            st.session_state.selected_position = None
            st.session_state.current_question = None
            st.session_state.asked_questions = set()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Ask me anything to start your interview practice!"}]

    if "selected_position" not in st.session_state:
        st.session_state.selected_position = None

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

    # Resume Analysis and Feedback
    if resume_text and st.session_state.selected_position:
        st.subheader("Resume Analysis")
        resume_feedback = analyze_resume(resume_text, st.session_state.selected_position, job_description_text)
        st.markdown(resume_feedback)

    # Job Description Analysis and Question Generation
    if job_description_text and st.session_state.selected_position:
        st.subheader("Job Description Analysis")
        jd_feedback = analyze_job_description(job_description_text)
        st.markdown(jd_feedback)

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Continuous question handling
    def llm_function(query):
        selected_position = st.session_state.selected_position
        context = st.session_state.messages

        if selected_position:
            # Generate feedback for the user's response
            feedback = generate_content(query, selected_position, context)
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.messages.append({"role": "assistant", "content": feedback})

            with st.chat_message("assistant"):
                st.markdown(feedback)

            # Clear current question to prompt generation of a new one
            st.session_state.current_question = None

        # Generate a new question if there are fewer questions asked than the limit (optional)
        if not st.session_state.current_question:
            # Generate a new question based on the job position
            question = generate_content(query, selected_position, context, is_question=True)
            st.session_state.current_question = question
            st.session_state.asked_questions.add(question)

            # Display the new question
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})
            with st.chat_message("assistant"):
                st.markdown(st.session_state.current_question)

    # User input handling
    query = st.chat_input("Your response here...")

    if query and st.session_state.selected_position:
        with st.chat_message("user"):
            st.markdown(query)
        llm_function(query)
    elif query and not st.session_state.selected_position:
        st.warning("Please select a job position from the sidebar before starting the interview.")

if __name__ == "__main__":
    main()
