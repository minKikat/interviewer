import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def generate_content(query, position, context, is_question=False):
    if len(context) >= 2:
        question_content = f"* **Question:** {context[-2]['content']}\n"
    else:
        question_content = ""

    if is_question:
        system_content = (
            f"You are an experienced HR interviewer specializing in {position} interviews. "
            f"Please generate a new interview question relevant to the position of {position}. The interview question should not be too long."
        )
    else:
        system_content = (
        f"You are an experienced HR interviewer specializing in {position} interviews. Your goal is to provide constructive feedback that helps the candidate improve their interview skills.\n\n"
        f"{question_content}"
        f"* **User's Response:** {query}\n\n"
        "Evaluate the user's response based on relevance, clarity, technical accuracy, communication skills, and problem-solving skills. "
        "If the response is irrelevant, unclear, or nonsensical acknowledge that the response doesn't address the question and encourage the user to focus on the relevant aspects. "
        "Provide tips or exaple better answer on how to answer the question effectively, such as asking for specific examples or encouraging the use of a structured response. "
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

def analyze_resume(resume_text, position):
    """Analyzes resume content with AI, optionally including job description."""
    it_keywords = ["software", "data", "computer science", "IT", "developer", "programming", "engineering", "network", "cloud"]
    
    # Check if resume has IT-related keywords
    relevant = any(keyword in resume_text.lower() for keyword in it_keywords)
    is_irrelevant = not relevant

    if relevant:
        prompt = f"""
        You are an experienced {position} interviewer. Analyze the following resume content:
        {resume_text}

        Evaluate the resume based on the relevance for a {position} role. Focus on technical skills, relevant experience, and other qualifications.
        """
    else:
        # If resume is not relevant, give feedback and suggest a suitable position
        prompt = f"""
        You are an experienced career advisor. Analyze the following resume content:
        {resume_text}

        Identify reasons why this resume may not be suitable for a {position} role, and suggest alternative job positions that align better with the candidate's experience and skills.
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
    return response.text.strip(), is_irrelevant

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

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Ask me anything to start your interview practice!"}]

    if "selected_position" not in st.session_state:
        st.session_state.selected_position = None

    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    if "asked_questions" not in st.session_state:
        st.session_state.asked_questions = set()

    resume_file = st.file_uploader("Upload Your Resume (PDF)", type="pdf")

    resume_text = ""
    is_irrelevant = False

    if resume_file:
        resume_text = extract_text_from_pdf(resume_file)
        st.success("Resume uploaded and extracted successfully!")

    if resume_text and st.session_state.selected_position:
        st.subheader("Resume Analysis")
        resume_feedback, is_irrelevant = analyze_resume(resume_text, st.session_state.selected_position)
        
        st.markdown(resume_feedback)

        # If the resume is irrelevant, display feedback and end chat
        if is_irrelevant:
            st.warning("Your resume does not match the requirements for this position. This concludes the session. Please explore other positions that may align better with your background.")
            st.stop()  # This stops the execution and prevents further input

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    def llm_function(query):
        selected_position = st.session_state.selected_position
        context = st.session_state.messages

        if selected_position:
            feedback = generate_content(query, selected_position, context)
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.messages.append({"role": "assistant", "content": feedback})

            with st.chat_message("assistant"):
                st.markdown(feedback)

            st.session_state.current_question = None

        if not st.session_state.current_question:
            question = generate_content(query, selected_position, context, is_question=True)
            st.session_state.current_question = question
            st.session_state.asked_questions.add(question)

            st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})
            with st.chat_message("assistant"):
                st.markdown(st.session_state.current_question)

    # Only show the input box if the resume is relevant
    if not is_irrelevant:
        query = st.chat_input("Your response here...")

        if query and st.session_state.selected_position:
            with st.chat_message("user"):
                st.markdown(query)
            llm_function(query)
        elif query and not st.session_state.selected_position:
            st.warning("Please select a job position from the sidebar before starting the interview.")

if __name__ == "__main__":
    main()
