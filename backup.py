import streamlit as st
import google.generativeai as genai
import os
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO

# --- Configuration ---
try:
    GEMINI_API_KEY = "AIzaSyAgavEmoD7FLNJHTuxef2wCdx9sAl8t_lw"
    genai.configure(api_key=GEMINI_API_KEY)
except (FileNotFoundError, KeyError):
    st.sidebar.warning("GEMINI_API_KEY not found in st.secrets. Please enter it below.")
    GEMINI_API_KEY = st.sidebar.text_input("Enter your Gemini API Key:", type="password")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)

# --- MBTI Data ---
MBTI_DESCRIPTIONS = {
    "INTJ": "As an INTJ, you're a strategic thinker, known for your logic, creativity, and drive. You appreciate directness and well-reasoned ideas. Your mentor will respect your independence and offer clear, logical perspectives.",
    "INTP": "As an INTP, you're an innovative inventor, fascinated by logical analysis and complex systems. You value intellectual connection and precision. Your mentor will engage your curiosity and explore possibilities with you.",
    "ENTJ": "As an ENTJ, you're a bold commander, a natural leader who is decisive and loves a good challenge. You thrive on momentum and accomplishment. Your mentor will be a strategic partner, helping you channel your energy effectively.",
    "ENTP": "As an ENTP, you're a clever debater, always questioning the status quo and exploring new ideas. You are quick-witted and enjoy intellectual sparring. Your mentor will brainstorm with you and challenge your ideas constructively.",
    "INFJ": "As an INFJ, you're a quiet advocate, driven by your strong values and a desire to help others. You are insightful and compassionate. Your mentor will listen deeply and help you navigate your rich inner world.",
    "INFP": "As an INFP, you are a thoughtful mediator, guided by your core values and a vivid imagination. You are empathetic and seek harmony. Your mentor will be a gentle guide, supporting your journey of self-discovery.",
    "ENFJ": "As an ENFJ, you're a charismatic protagonist, inspiring others with your passion and idealism. You are a natural connector of people. Your mentor will be an encouraging coach, helping you realize your vision.",
    "ENFP": "As an ENFP, you're a creative campaigner, full of energy and a desire to connect with others on an emotional level. You are enthusiastic and imaginative. Your mentor will be a supportive friend, celebrating your ideas and spirit.",
    "ISTJ": "As an ISTJ, you're a practical logistician, known for your reliability, integrity, and dedication to facts. You value structure and order. Your mentor will provide dependable, fact-based guidance.",
    "ISFJ": "As an ISFJ, you're a warm defender, dedicated to protecting and caring for the people you love. You are meticulous and kind-hearted. Your mentor will be a source of steady, compassionate support.",
    "ESTJ": "As an ESTJ, you're an effective executive, a pillar of your community who values order and tradition. You are organized and honest. Your mentor will offer practical advice to help you manage your responsibilities.",
    "ESFJ": "As an ESFJ, you're a caring consul, a popular and supportive friend who is always eager to help. You thrive in social harmony. Your mentor will be a warm and encouraging presence.",
    "ISTP": "As an ISTP, you're a hands-on virtuoso, a natural maker and troubleshooter who loves to understand how things work. You are practical and action-oriented. Your mentor will focus on concrete steps and tangible solutions.",
    "ISFP": "As an ISFP, you're a charming adventurer, always ready to explore and experience something new. You are artistic and live in the moment. Your mentor will encourage your creativity and unique perspective.",
    "ESTP": "As an ESTP, you're an energetic entrepreneur, living life on the edge with a love for action and immediate results. You are perceptive and sociable. Your mentor will keep things engaging and focus on the here-and-now.",
    "ESFP": "As an ESFP, you're a spontaneous entertainer, lighting up any room with your energy and love for life. You are vivacious and generous. Your mentor will be a fun and engaging supporter of your journey."
}
# --- Helper Functions ---
def generate_system_prompt(mbti_type, financial_info, orientation_info, narrative_mode_enabled):
    """Creates a detailed system prompt for the Gemini model."""
    description = MBTI_DESCRIPTIONS.get(mbti_type, "a unique individual")
    
    prompt = f"""
    You are "Aura," a empathetic, and supportive friend. You are NOT a psychiatrist. Your goal is to listen the user's problem and suggest genuine solutions or provide emotional support to the user.

    Your current user has identified their personality type as {mbti_type}. {description}
    
    KEY INSTRUCTIONS:
    1.  **Persona**: Be warm, friendly, and use encouraging language. Use emojis where appropriate to convey warmth.
    2.  **MBTI-Informed**: Keep the user's {mbti_type} traits in mind. For example, be more logical with a 'T' type and more value-focused with an 'F' type. I hope the rest you understand.
    3.  **Show Concern**: Try to make a impact in positive user's life. LIKE, help them get rid of bad habits or toxic friends.
    4.  **Advice**: You can give them advice based on the data they have given you like there financial status or sexual orientation and MBTI type.
    5.  **CRISIS PROTOCOL**: If the user mentions self-harm, suicide, wanting to die, or being in immediate danger, you MUST ONLY respond with the following message and nothing else:
        "It sounds like you are going through a very difficult time, and it's important to talk to someone who can help you stay safe right now. Please reach out to a crisis hotline immediately. In India, you can connect with AASRA at +91-9820466726. Help is available and you deserve support."
    """
    
    if narrative_mode_enabled:
        prompt += f"""
    6.  **NARRATIVE MODE**: After your main response, you may suggest upto 3 short, follow-up options for the user to click. These options should be based on your reply and there goal is to keep the conversation going, to keep the user engaged to your talk. Keep them concise (5-10 words). Format these options EXACTLY as follows on new lines, after your main reply, starting with the separator '---OPTIONS---':
        ---OPTIONS---
        - First option
        - Second option
        - Third option
    """
        
    if financial_info and financial_info.strip():
        prompt += f"\n- The user has optionally shared this about their financial situation: '{financial_info}'. Be mindful of this context without making assumptions."
    if orientation_info and orientation_info.strip():
        prompt += f"\n- The user has optionally shared this about their sexual orientation: '{orientation_info}'. Be respectful and inclusive of this identity."
        
    return prompt

def transcribe_audio(audio_bytes):
    """Converts audio bytes to WAV format in memory and then transcribes to text."""
    try:
        audio = AudioSegment.from_file(BytesIO(audio_bytes))
        wav_io = BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        st.warning("Aura couldn't understand the audio. Please try again.")
        return None
    except Exception as e:
        st.error(f"An error occurred during transcription: {e}")
        return None

# --- Streamlit App ---

st.set_page_config(page_title="Aura - Your Peer Mentor", page_icon="💖")
st.title("💖 Aura: Your Supportive Peer Mentor")
st.caption("A safe space to chat, powered by Gemini and tailored to your personality.")

# --- Initialization and Setup ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model" not in st.session_state:
    st.session_state.model = None
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None
if "recorder_counter" not in st.session_state:
    st.session_state.recorder_counter = 0
if "narrative_mode" not in st.session_state:
    st.session_state.narrative_mode = True # Default to on
if "last_options" not in st.session_state:
    st.session_state.last_options = []

# --- Main App Logic ---
if not GEMINI_API_KEY:
    st.info("Please provide your Gemini API Key in the sidebar to begin.")
    st.stop()
    
# --- START OF MOVED CODE ---
# These widgets are now here, so they will always appear in the sidebar.
st.session_state.narrative_mode = st.sidebar.toggle(
    "Enable Narrative Conversation",
    value=st.session_state.narrative_mode,
    help="Aura will suggest replies to help guide the conversation."
)

if st.sidebar.button("Start New Chat"):
    st.session_state.messages = []
    st.session_state.model = None
    st.session_state.last_audio_id = None
    st.session_state.recorder_counter = 0
    st.session_state.narrative_mode = True
    st.session_state.last_options = []
    st.rerun()
# --- END OF MOVED CODE ---

# Show setup screen only if the chat has not started
if st.session_state.model is None:
    st.markdown("""
    **Welcome!** I'm here to listen. To help me understand you better, please share your MBTI personality type, it helps me know more about you.
    If you don't know your type, you can take a free test at [16Personalities](https://www.16personalities.com/free-personality-test).
    """)
    # <<< ADD THIS CODE HERE
    with st.expander("What is MBTI? Click to learn more..."):
        st.markdown("""
        The MBTI was built on the theories of the Swiss psychiatrist Carl Jung, but he didn't create the personality test himself. The actual creators were an American mother-daughter team, Katharine Cook Briggs and Isabel Myers. It looks at four key areas:

        * **Where you get your energy:** From the inner world (Introversion - I) or the outer world (Extraversion - E).
        * **How you process information:** Focusing on facts and details (Sensing - S) or patterns and possibilities (Intuition - N).
        * **How you make decisions:** Based on logic and reason (Thinking - T) or values and people (Feeling - F).
        * **How you prefer to live:** In a planned, organized way (Judging - J) or a more spontaneous, flexible way (Perceiving - P).

        Your four preferences combine to make up your unique personality type!
        """)
    # --- END OF NEW CODE ---
    mbti_type = st.selectbox("Select your MBTI Personality Type:", options=list(MBTI_DESCRIPTIONS.keys()))
    
    st.markdown("---")
    with st.expander("Optional: Share more context (helps Aura understand you better)"):
        financial_info = st.text_input("Financial Situation (e.g., student, working, concerned about money)")
        orientation_info = st.text_input("Sexual Orientation (e.g., LGBTQ+, questioning, prefer not to say)")
    
    st.markdown("---")
    problem = st.text_area("What's on your mind today? (Please be as brief or as detailed as you like)", height=150)

    if st.button("Start Chat with Aura"):
        if problem.strip():
            system_instruction = generate_system_prompt(mbti_type, financial_info, orientation_info, st.session_state.narrative_mode)
            st.session_state.model = genai.GenerativeModel(
                model_name="gemini-2.5-pro", 
                system_instruction=system_instruction
            )
            st.session_state.messages.append({"role": "user", "parts": [problem]})
            
            with st.spinner("Aura is thinking..."):
                response = st.session_state.model.generate_content(st.session_state.messages)
                full_response = response.text
                main_text = full_response
                options = []

                if st.session_state.narrative_mode and "---OPTIONS---" in full_response:
                    try:
                        parts = full_response.split("---OPTIONS---", 1)
                        main_text = parts[0].strip()
                        options_str = parts[1].strip()
                        options = [opt.strip().lstrip('- ') for opt in options_str.split('\n') if opt.strip()]
                    except Exception:
                        main_text = full_response
                        options = []
            
            st.session_state.messages.append({"role": "model", "parts": [main_text]})
            st.session_state.last_options = options
            st.rerun()
        else:
            st.warning("Please share what's on your mind to start the chat.")
else:
    # --- Chat Interface ---
    st.success("You are now chatting with Aura.")

    # NOTE: The sidebar buttons were removed from here.

    # --- Helper function to process any prompt ---
    def handle_prompt(prompt_text):
        """Processes a given prompt, gets a response, and reruns the app."""
        if not prompt_text or not prompt_text.strip():
            return # Don't process empty prompts

        st.session_state.messages.append({"role": "user", "parts": [prompt_text]})

        with st.spinner("Aura is thinking..."):
            response = st.session_state.model.generate_content(st.session_state.messages)
            full_response = response.text
            main_text = full_response
            options = []

            if st.session_state.narrative_mode and "---OPTIONS---" in full_response:
                try:
                    parts = full_response.split("---OPTIONS---", 1)
                    main_text = parts[0].strip()
                    options_str = parts[1].strip()
                    options = [opt.strip().lstrip('- ') for opt in options_str.split('\n') if opt.strip()]
                except Exception:
                    # If parsing fails, just use the full response
                    main_text = full_response
                    options = []
        
        st.session_state.messages.append({"role": "model", "parts": [main_text]})
        st.session_state.last_options = options
        st.session_state.recorder_counter += 1
        st.rerun()

    # Display existing messages
    for message in st.session_state.messages:
        with st.chat_message("user" if message["role"] == "user" else "assistant", avatar="🧑‍💻" if message["role"] == "user" else "💖"):
            st.markdown(message["parts"][0])

    # --- INPUT WIDGETS ---

    # 1. Narrative Buttons
    if st.session_state.narrative_mode and st.session_state.last_options:
        button_container = st.container()
        with button_container:
            cols = st.columns(len(st.session_state.last_options))
            for i, option in enumerate(st.session_state.last_options):
                if cols[i].button(option, key=f"option_{i}_{st.session_state.recorder_counter}"):
                    st.session_state.last_options = [] # Clear options to prevent re-clicks
                    handle_prompt(option) # Call handler immediately and exit script via rerun

    # 2. Audio Input
    st.write("Talk to Aura:")
    audio_data = mic_recorder(
        start_prompt="🎤 Start Recording",
        stop_prompt="⏹️ Stop Recording",
        key=f'recorder_{st.session_state.recorder_counter}'
    )
    if audio_data and audio_data['id'] != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_data['id']
        with st.spinner("Transcribing your voice..."):
            audio_prompt = transcribe_audio(audio_data['bytes'])
            handle_prompt(audio_prompt) # Call handler immediately

    # 3. Text Input (st.chat_input should be the last interactive widget)
    if text_prompt := st.chat_input("Or type your message here..."):

        handle_prompt(text_prompt)
