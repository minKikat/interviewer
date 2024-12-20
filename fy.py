import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
#import openai
import random

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
#openai.api_key = os.getenv("OPENAI_API_KEY")

# Predefined questions for each job position
job_questions = {
    "Software Engineer": [
        "What programming languages are you proficient in?",
        "How do you approach debugging a program?",
        "Tell me about a challenging project you've worked on."
    ],
    "Data Scientist": [
        "What experience do you have with data analysis?",
        "How do you handle missing data in a dataset?",
        "Explain a machine learning project you’ve worked on."
    ],
    "DevOps Engineer": [
        "What tools do you use for continuous integration?",
        "How would you set up an automated deployment pipeline?",
        "Describe a time when you improved the reliability of a system."
    ],
    "Product Manager": [
        "How do you prioritize features in a product roadmap?",
        "Tell me about a time you handled conflicting stakeholder feedback.",
        "How do you measure the success of a product?"
    ]
}

def generate_content(query, position, context):
    system_content = f"""
    You are an experienced HR interviewer specializing in {position} interviews. Your goal is to provide constructive feedback that helps the candidate improve their interview skills. "

    **Here's the scenario:**
    * **Question:** {context[-1]['content']}
    * **User's Response:** {query}

    **Please evaluate the user's response based on the following criteria:**
    1. **Relevance:** Does the response directly address the question?
    2. **Clarity and Conciseness:** Is the response clear, concise, and easy to understand?
    3. **Technical Accuracy:** Are the technical concepts explained correctly?
    4. **Communication Skills:** Does the response demonstrate effective communication skills, such as active listening, clear articulation, and persuasive language?
    5. **Problem-Solving Skills:** Does the response demonstrate the ability to think critically, analyze problems, and propose solutions?

    **Provide specific, actionable feedback in a supportive and encouraging tone.** 
    * **Identify strengths:** Highlight the positive aspects of the response.
    * **Point out areas for improvement:** Offer constructive criticism and specific suggestions.
    * **Provide examples:** Illustrate your feedback with concrete examples.
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    
    response = model.generate_content(
        system_content,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            #stop_sequences=["x"],
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
                st.session_state.valid_answer = False  # Track if answer is valid

        if st.button("Clear Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Ask me anything to start your interview practice!"}
            ]
            st.session_state.selected_position = None
            st.session_state.current_question = None
            st.session_state.asked_questions = set()
            st.session_state.valid_answer = False

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Ask me anything to start your interview practice!"}]

    if "selected_position" not in st.session_state:
        st.session_state.selected_position = None

    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    if "asked_questions" not in st.session_state:
        st.session_state.asked_questions = set()

    if "valid_answer" not in st.session_state:
        st.session_state.valid_answer = False

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Continuous question handling
    def llm_function(query):
        selected_position = st.session_state.selected_position
        context = st.session_state.messages

        if selected_position:
            # Generate feedback about whether the user's answer is relevant
            response = generate_content(query, selected_position, context)
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.messages.append({"role": "assistant", "content": response})

            with st.chat_message("assistant"):
                st.markdown(response)

            # Clear current question to allow the next one to be asked
            st.session_state.current_question = None

        # Only ask the next question if the current question has been answered
        if not st.session_state.current_question and len(st.session_state.asked_questions) < len(job_questions[selected_position]):
            next_question = random.choice(
                [q for q in job_questions[selected_position] if q not in st.session_state.asked_questions]
            )
            st.session_state.current_question = next_question
            st.session_state.asked_questions.add(next_question)

            # Display the current question
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_question})
            with st.chat_message("assistant"):
                st.markdown(st.session_state.current_question)

        elif len(st.session_state.asked_questions) >= len(job_questions[selected_position]):
            st.session_state.messages.append(
                {"role": "assistant", "content": "You have completed all the questions for this position!"}
            )
            with st.chat_message("assistant"):
                 st.markdown("You have completed all the questions for this position!")

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

