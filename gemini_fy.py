import google.generativeai as genai
import os
import streamlit as st
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def main():
    st.set_page_config(page_title="Interviewer ChatBot AI", page_icon="🤖", layout="wide")
    st.title("Interviewer ChatBot AI")

    # === Sidebar for Job Selection ===
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

        # Select IT Job Position
        st.subheader("Select IT Job Position")
        job_positions = ["Software Engineer", "Data Scientist", "DevOps Engineer", "Product Manager"]

        for position in job_positions:
            if st.button(position):
                st.session_state.selected_position = position
                st.session_state.messages = [
                    {"role": "assistant", "content": f"Let's start the interview for the {position} position. Tell me about yourself."}
                ]
                st.session_state.question_index = 0
                st.session_state.next_question = False

        # Clear Chat button
        if st.button("Clear Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Ask me anything to start your interview practice!"}
            ]
            st.session_state.selected_position = None
            st.session_state.next_question = True
            st.session_state.question_index = 0

    # Function to Generate AI Feedback without Token Limit
    def generate_content(query, position):
        system_content = f"You are an experienced HR interviewer with a background in IT, specializing in {position} interviews. The user has responded to: {query}. Suggest how to improve the response, simulate a back-and-forth interview practice, and ask the next question only when prompted."

        model = genai.GenerativeModel("gemini-1.5-flash")
        response_text = ""
        continuation_prompt = "Please continue from where you left off."

        while True:
            response = model.generate_content(
                system_content,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    stop_sequences=["x"],
                    temperature=0.7,
                )
            )

            # Append the response text
            response_text += response.text.strip()
            print("Generated response part:", response.text.strip())  # Debugging

            # Check if the response likely completed, or if continuation is needed
            if len(response.text.strip()) < 500 or response.text.strip().endswith("."):
                break
            else:
                # Request continuation
                system_content = continuation_prompt

        return response_text.strip()

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
            if not st.session_state.next_question:
                response = generate_content(query, selected_position)

                # Record messages
                st.session_state.messages.append({"role": "user", "content": query})
                st.session_state.messages.append({"role": "assistant", "content": response})

                # Display response in parts for Streamlit
                with st.chat_message("assistant"):
                    response_parts = [response[i:i+1000] for i in range(0, len(response), 1000)]
                    for part in response_parts:
                        st.markdown(part)

                st.session_state.next_question = True
            else:
                st.session_state.next_question = False

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
