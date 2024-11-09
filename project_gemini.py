import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import openai
import random

# Load environment variables
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    system_content = (
        f"You are an experienced HR interviewer with a background in IT, specializing in {position} interviews. "
        f"The user has just responded to the following question: {context[-1]['content']}. "
        "Check if the user's response is addressing the core concepts of the question. "
        "The user is asked about how to handle missing data in a dataset. Look for responses mentioning key strategies like "
        "imputation, deletion, understanding the pattern of missing data, or machine learning-based approaches. "
        "If the answer doesn't cover these aspects or feels completely off-topic, respond with: "
        "'Your answer is not related to the question. Please try to provide a relevant answer.' "
        "Otherwise, acknowledge the response and briefly assess the technical depth or clarity."
    )

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        system_content,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            stop_sequences=["x"],
            max_output_tokens=500,
            temperature=0.7,
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

            # Check if the answer is relevant
            if "not related" in response:
                # If the answer is not relevant, do not proceed to next question
                st.session_state.valid_answer = False
                return  # Wait for the user to provide a relevant answer

            # If the answer is relevant, proceed to the next question
            st.session_state.valid_answer = True

        # Ask the next question only if the previous answer was valid
        if st.session_state.valid_answer:
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

                # Reset the valid_answer flag after asking the next question
                st.session_state.valid_answer = False

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

