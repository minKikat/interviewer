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
                st.session_state.next_question = False  # Ready to ask the next question

        # Add Clear Chat button
        if st.button("Clear Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Ask me anything to start your interview practice!"}
            ]
            st.session_state.selected_position = None
            st.session_state.next_question = True
            st.session_state.question_index = 0

    # Function to generate AI feedback
    def generate_content(query, position):
        system_content = f"You are an experienced HR interviewer with a background in IT, specializing in {position} interviews. The user has just responded to the following question: {query}. Make suggestions to the user on how to better answer the interview question, provide practice to the user as if the interviewer is asking the same question back and forth, and then finally make suggestions on how to better answer the questions. Only after the user has answered a question can you ask the next question, and only when the user says it's over can you summarize how to improve the answer."

        # Use the new Chat API
        model = genai.GenerativeModel("gemini-1.5-flash")  # or "gpt-4" if available
        response = model.generate_content(
            system_content,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                stop_sequences=["x"],
                max_output_tokens=2000,  # Adjust as needed
                temperature=0.7,
            )
        )

        return response.text.strip()

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
            # 判断是否要生成下一个问题
            if not st.session_state.next_question:
                # 动态生成下一个问题
                response = generate_content(query, selected_position)

                # 记录用户和 AI 消息
                st.session_state.messages.append({"role": "user", "content": query})
                st.session_state.messages.append({"role": "assistant", "content": response})

                # 显示生成的问题
                with st.chat_message("assistant"):
                    st.markdown(response)

                # 重置 next_question 状态，等待用户下一次回答
                st.session_state.next_question = True
            else:
                # 准备好下一个问题
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








