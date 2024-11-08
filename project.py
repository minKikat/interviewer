import os
import streamlit as st
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def main():
    st.set_page_config(page_title="Interviewer ChatBot AI", page_icon="🤖", layout="wide")
    st.title("Interviewer ChatBot AI")

    # === Add Sidebar (Sidebar) ===
    with st.sidebar:
        st.header("📝 About This App")
        st.markdown(
            """
            **Interviewer ChatBot AI**  
            This AI assistant helps you practice interview questions.  
            - Simulates HR interview scenarios  
            - Provides feedback and suggestions  
            - Supports continuous back-and-forth practice
            """
        )

        # Add IT Job Position buttons
        st.subheader("Select IT Job Position")
        job_positions = ["Software Engineer", "Data Scientist", "DevOps Engineer", "Product Manager"]

        # Check which job position the user selected
        for position in job_positions:
            if st.button(position):
                st.session_state.selected_position = position
                st.session_state.messages = [
                    {"role": "assistant", "content": f"Let's start the interview for the {position} position. Tell me about yourself."}
                ]
                st.session_state.question_index = 0  # Reset question index
                st.session_state.next_question = True  # Ready to ask the next question

        # Add Clear Chat button
        if st.button("Clear Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Ask me anything to start your interview practice!"}
            ]
            st.session_state.selected_position = None
            st.session_state.next_question = False
            st.session_state.question_index = 0

    # Function to get next question for the selected position
    def get_next_question(position):
        questions = {
            "Software Engineer": [
                "What is your experience with software development?",
                "Can you explain the difference between a stack and a queue?",
                "Describe a challenging project you have worked on."
            ],
            "Data Scientist": [
                "How do you approach cleaning and preprocessing data?",
                "Explain the concept of overfitting in machine learning.",
                "Describe a data analysis project you are proud of."
            ],
            "DevOps Engineer": [
                "What tools have you used for CI/CD pipelines?",
                "Explain how you manage system monitoring and alerts.",
                "How do you handle system failures or downtimes?"
            ],
            "Product Manager": [
                "How do you prioritize product features?",
                "Describe a time when you had to handle conflicting stakeholder interests.",
                "How do you measure the success of a product?"
            ]
        }
        return questions.get(position, [])

    # Function to generate AI feedback
    def generate_content(query, position):
        system_content = f"You are an experienced HR interviewer with a background in IT, specializing in {position} interviews. Make suggestions to the user on how to better answer the interview questions, provide practice to the user as if the interviewer is asking the same questions back and forth, and then finally make suggestions on how to better answer the questions. Only after the user has answered a question can you ask the next question, and only when the user says it's over can you summarize how to improve the answer."

        # Use the new Chat API
        response = openai.ChatCompletion.create(
            model="Gemini Pro",  # or "gpt-4" if available
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=150,
        )
        return response.choices[0].message["content"].strip()

    # Initialize session state if not already done
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Ask me anything to start your interview practice!"}
        ]
    if "selected_position" not in st.session_state:
        st.session_state.selected_position = None
    if "next_question" not in st.session_state:
        st.session_state.next_question = False
    if "question_index" not in st.session_state:
        st.session_state.question_index = 0

    # Display previous chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Function to handle continuous question asking
    def llm_function(query):
        selected_position = st.session_state.selected_position
        if selected_position:
            questions = get_next_question(selected_position)

            # Check if there are more questions to ask
            if st.session_state.question_index < len(questions):
                # Generate AI feedback after the user's answer
                if not st.session_state.next_question:
                    response = generate_content(query, selected_position)

                    # Store user and AI messages
                    st.session_state.messages.append({"role": "user", "content": query})
                    st.session_state.messages.append({"role": "assistant", "content": response})

                    # Set up for the next question
                    st.session_state.next_question = True

                # Ask the next question
                if st.session_state.next_question:
                    current_question = questions[st.session_state.question_index]
                    with st.chat_message("assistant"):
                        st.markdown(current_question)

                    # Update index and prepare for user's response
                    st.session_state.question_index += 1
                    st.session_state.next_question = False
            else:
                with st.chat_message("assistant"):
                    st.markdown("You have completed the interview questions. Do you want to ask anything else?")

    # Receive user input
    query = st.chat_input("Your response here...")

    # Handle input from the user
    if query and st.session_state.selected_position:
        with st.chat_message("user"):
            st.markdown(query)
        llm_function(query)
    elif query and not st.session_state.selected_position:
        st.warning("Please select a job position from the sidebar before starting the interview.")

if __name__ == "__main__":
    main()



