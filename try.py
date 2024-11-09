import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import random
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()

# Configure the Google Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Predefined questions for each job position
job_questions = {
    "Software Engineer": [
        "What programming languages are you proficient in?",
        "How do you approach debugging a program?",
        "Tell me about a challenging project you've worked on.",
        "Design a URL shortening service like Bit.ly. What components would you include, and how would you design it for scalability?",
    ],
    "Data Scientist": [
        "What experience do you have with data analysis?",
        "How do you handle missing data in a dataset?",
        "Explain a machine learning project you’ve worked on.",
    ],
    "DevOps Engineer": [
        "What tools do you use for continuous integration?",
        "How would you set up an automated deployment pipeline?",
    ],
    "Product Manager": [
        "How do you prioritize features in a product roadmap?",
        "Tell me about a time you handled conflicting stakeholder feedback.",
    ]
}

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
    
    Provide a summary of the key qualifications, skills, and experience required for this role, and suggest any areas where the candidate might need to improve or focus on.
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

def generate_content(query, position, context):
    """Generates feedback based on the interview question and user response."""
    system_content = f"""
    You are an experienced HR interviewer specializing in {position} interviews. Provide constructive feedback for the candidate's improvement.
    
    **Scenario:**
    * **Question:** {context[-1]['content']}
    * **User's Response:** {query}

    **Feedback Criteria:**
    1. **Relevance:** Does the response directly address the question?
    2. **Clarity and Conciseness:** Is the response clear, concise, and easy to understand?
    3. **Technical Accuracy:** Are technical concepts explained correctly?
    4. **Communication Skills:** Is communication clear, with effective articulation?
    5. **Problem-Solving Skills:** Does the response show critical thinking?

    **Provide specific, actionable feedback in a supportive and encouraging tone.** 
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    response = model.generate_content(
        system_content,
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
            This AI assistant helps you practice interview questions and provides feedback on your resume.
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

        # Upload and analyze resume
        st.subheader("Upload Resume")
        resume_file = st.file_uploader("Upload your resume in PDF format", type=["pdf"])

        # Upload and analyze job description
        st.subheader("Upload Job Description")
        job_description_file = st.file_uploader("Upload the job description in PDF format", type=["pdf"])
        
        job_description_text = None
        if job_description_file:
            job_description_text = extract_text_from_pdf(job_description_file)
            
            if job_description_text:
                with st.spinner("Analyzing the job description..."):
                    job_description_feedback = analyze_job_description(job_description_text)
                    # Store the analysis result in session state and automatically show it
                    st.session_state.messages.append({"role": "assistant", "content": job_description_feedback})
                    st.success("Job description analysis complete. Check the main chat window for feedback.")

        if resume_file and "selected_position" in st.session_state:
            # Extract text from uploaded resume
            resume_text = extract_text_from_pdf(resume_file)
            
            # Analyze resume only after job description is processed (optional)
            with st.spinner("Analyzing your resume..."):
                resume_feedback = analyze_resume(resume_text, st.session_state.selected_position, job_description_text)
                st.session_state.messages.append({"role": "assistant", "content": resume_feedback})
                st.success("Resume analysis complete. Check the main chat window for feedback.")
            
            # Start interview by asking the first question
            if st.session_state.selected_position in job_questions:
                first_question = random.choice(job_questions[st.session_state.selected_position])
                st.session_state.current_question = first_question
                st.session_state.asked_questions.add(first_question)
                st.session_state.messages.append({"role": "assistant", "content": first_question})
                with st.chat_message("assistant"):
                    st.markdown(first_question)

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Ask me anything to start your interview practice!"}]

    if "selected_position" not in st.session_state:
        st.session_state.selected_position = None

    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    if "asked_questions" not in st.session_state:
        st.session_state.asked_questions = set()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Continuous question handling
    def llm_function(query):
        selected_position = st.session_state.selected_position
        context = st.session_state.messages

        if selected_position:
            response = generate_content(query, selected_position, context)
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.messages.append({"role": "assistant", "content": response})

            with st.chat_message("assistant"):
                st.markdown(response)

            st.session_state.current_question = None

        if not st.session_state.current_question and len(st.session_state.asked_questions) < len(job_questions[selected_position]):
            next_question = random.choice(
                [q for q in job_questions[selected_position] if q not in st.session_state.asked_questions]
            )
            st.session_state.current_question = next_question
            st.session_state.asked_questions.add(next_question)

            st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})
            with st.chat_message("assistant"):
                st.markdown(st.session_state.current_question)

    # User input
    query = st.chat_input("Your response here...")

    if query and st.session_state.selected_position:
        with st.chat_message("user"):
            st.markdown(query)
        llm_function(query)
    elif query and not st.session_state.selected_position:
        st.warning("Please select a job position from the sidebar before starting the interview.")

if __name__ == "__main__":
    main()
