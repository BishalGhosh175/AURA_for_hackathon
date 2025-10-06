import streamlit as st
import google.generativeai as genai
import os
import sqlite3
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO
from collections import Counter
import json

# --- Configuration ---
GOOGLE_API_KEY = "" 

try:
    # Recommended: Use Streamlit's secrets management
    GOOGLE_API_KEY = "AIzaSyBr1urJ1Nwlj2PdN6PF904Kcn0QXZ2ETZg"
except (FileNotFoundError, KeyError):
    st.sidebar.warning("Google API Key not found in st.secrets. Please enter it below.")
    GOOGLE_API_KEY = st.sidebar.text_input("Enter your Google API Key:", type="password")

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        st.error(f"Error configuring Google API: {e}")
        st.stop()
else:
    st.info("Please provide your Google API Key in the sidebar to begin.")
    st.stop()


# --- MBTI Data (unchanged) ---
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
ADVANCED_MBTI_QUESTIONS = [
    {"question": "I feel energized after spending time with a large group of people.", "dimension": "E/I", "direction": 1},
    {"question": "I prefer one-on-one conversations over group activities.", "dimension": "E/I", "direction": -1},
    {"question": "I am often the one to initiate conversations.", "dimension": "E/I", "direction": 1},
    {"question": "I need a lot of private time to recharge.", "dimension": "E/I", "direction": -1},
    {"question": "I enjoy being the center of attention.", "dimension": "E/I", "direction": 1},
    {"question": "I focus on concrete details and facts rather than the big picture.", "dimension": "S/N", "direction": 1},
    {"question": "I am more intrigued by future possibilities than present realities.", "dimension": "S/N", "direction": -1},
    {"question": "I trust experience and what is proven more than theories.", "dimension": "S/N", "direction": 1},
    {"question": "I often think about the deeper meaning or symbolism of things.", "dimension": "S/N", "direction": -1},
    {"question": "When solving a problem, I prefer to use established and reliable methods.", "dimension": "S/N", "direction": 1},
    {"question": "I enjoy discussing abstract concepts and ideas.", "dimension": "S/N", "direction": -1},
    {"question": "I would describe myself as a realistic and practical person.", "dimension": "S/N", "direction": 1},
    {"question": "I make decisions with my head rather than my heart.", "dimension": "T/F", "direction": 1},
    {"question": "I prioritize harmony and the feelings of others when making choices.", "dimension": "T/F", "direction": -1},
    {"question": "I value truth and justice over tact and compassion.", "dimension": "T/F", "direction": 1},
    {"question": "I am easily affected by the emotional states of others.", "dimension": "T/F", "direction": -1},
    {"question": "I enjoy a logical debate, even if it becomes heated.", "dimension": "T/F", "direction": 1},
    {"question": "I like to have a clear plan and a to-do list.", "dimension": "J/P", "direction": 1},
    {"question": "I prefer to keep my options open and act spontaneously.", "dimension": "J/P", "direction": -1},
    {"question": "I feel a sense of accomplishment from finishing tasks well before the deadline.", "dimension": "J/P", "direction": 1},
    {"question": "I am adaptable and comfortable with last-minute changes.", "dimension": "J/P", "direction": -1},
    {"question": "I prefer a neat, organized environment.", "dimension": "J/P", "direction": 1},
]
LIKERT_SCALE_OPTIONS = ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"]
SCORE_MAPPING = {"Strongly Agree": 2, "Agree": 1, "Neutral": 0, "Disagree": -1, "Strongly Disagree": -2}
DIMENSION_COUNTS = Counter(q['dimension'] for q in ADVANCED_MBTI_QUESTIONS)

# --- Database Helper Functions (unchanged) ---
DB_FILE = "aura_users.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            name TEXT PRIMARY KEY,
            mbti_type TEXT NOT NULL,
            financial_info TEXT,
            orientation_info TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user(name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT mbti_type, financial_info, orientation_info FROM users WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

def save_user(name, mbti_type, financial_info, orientation_info):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    fin_info_to_save = financial_info.strip() if financial_info.strip() else "unknown"
    orient_info_to_save = orientation_info.strip() if orientation_info.strip() else "unknown"
    cursor.execute(
        "INSERT OR REPLACE INTO users (name, mbti_type, financial_info, orientation_info) VALUES (?, ?, ?, ?)",
        (name, mbti_type, fin_info_to_save, orient_info_to_save)
    )
    conn.commit()
    conn.close()

# --- Helper Functions (unchanged logic, updated prompts for Gemini) ---
def generate_system_prompt(user_name,mbti_type, financial_info, orientation_info, narrative_mode_enabled):
    """Creates a detailed system prompt for the Gemini model."""
    description = MBTI_DESCRIPTIONS.get(mbti_type, "a unique individual")
    
    prompt = f"""
    You are "Aura," a empathetic, and supportive friend. You are NOT a psychiatrist. Your goal is to listen the user's problem and suggest genuine solutions or provide emotional support to the user.

    Your current user has identified their personality type as {mbti_type}. {description}
    
    KEY INSTRUCTIONS:
    1.  **Persona**: Be warm, friendly, and use encouraging language. Address {user_name} by their name occasionally to build rapport. Use emojis where appropriate to convey warmth.
    2.  **MBTI-Informed**: Keep the user's {mbti_type} traits in mind. For example, be more logical with a 'T' type and more value-focused with an 'F' type. I hope the rest you understand.
    3.  **Show Concern**: Try to make a impact in positive user's life. LIKE, help them get rid of bad habits or toxic friends.
    4.  **Advice**: You can give them advice based on the data they have given you like there financial status or sexual orientation and MBTI type.
    5.  **CRISIS PROTOCOL**: If the user mentions self-harm, suicide, wanting to die, or being in immediate danger, you MUST ONLY respond with the following message and nothing else:
        "It sounds like you are going through a very difficult time, and it's important to talk to someone who can help you stay safe right now. Please reach out to a crisis hotline immediately. In India, you can connect with AASRA at +91-9820466726. Help is available and you deserve support."
    """
    
    if narrative_mode_enabled:
        prompt += f"""
        6.**NARRATIVE MODE**: After your main response, you may suggest upto 3 short, follow-up options for the user to click. These options should be based on your reply and there goal is to keep the conversation going, to keep the user engaged to your talk. Keep them concise (5-10 words). Format these options EXACTLY as follows on new lines, after your main reply, starting with the separator '---OPTIONS---':
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

def calculate_mbti_scores(answers):
    scores = {"E/I": 0, "S/N": 0, "T/F": 0, "J/P": 0}
    for i, answer in enumerate(answers):
        question = ADVANCED_MBTI_QUESTIONS[i]
        dimension = question["dimension"]
        direction = question["direction"]
        raw_score = SCORE_MAPPING[answer]
        scores[dimension] += raw_score * direction
    return scores

def interpret_scores(scores):
    results = {}
    def get_dimension_result(dim_name, letter1, letter2):
        score = scores[dim_name]
        max_score = DIMENSION_COUNTS[dim_name] * 2
        if score > 0:
            letter = letter1
            percentage = round((score / max_score) * 100)
        else:
            letter = letter2
            percentage = round((abs(score) / max_score) * 100)
        return letter, percentage
    results["E/I_Letter"], results["E/I_Percentage"] = get_dimension_result("E/I", "E", "I")
    results["S/N_Letter"], results["S/N_Percentage"] = get_dimension_result("S/N", "S", "N")
    results["T/F_Letter"], results["T/F_Percentage"] = get_dimension_result("T/F", "T", "F")
    results["J/P_Letter"], results["J/P_Percentage"] = get_dimension_result("J/P", "J", "P")
    mbti_type = (results["E/I_Letter"] + results["S/N_Letter"] +
                 results["T/F_Letter"] + results["J/P_Letter"])
    return mbti_type, results

def generate_placeholder_results(mbti_type):
    if not mbti_type or len(mbti_type) != 4:
        return None
    return {
        "E/I_Letter": mbti_type[0], "E/I_Percentage": "N/A",
        "S/N_Letter": mbti_type[1], "S/N_Percentage": "N/A",
        "T/F_Letter": mbti_type[2], "T/F_Percentage": "N/A",
        "J/P_Letter": mbti_type[3], "J/P_Percentage": "N/A"
    }

# --- Product Recommendation Engine ---
RECOMMENDATION_LOGIC = {
    'I': {'trait': "Introversion (I)", 'tendency': "Driven by enriching their inner world. Researches thoroughly, buys for solitary use, and values long-term quality."},
    'E': {'trait': "Extraversion (E)", 'tendency': "Energized by social interaction. Influenced by trends, prefers spending on experiences and items that enhance status."},
    'S': {'trait': "Sensing (S)", 'tendency': "Trusts what is tangible and proven. Focuses on facts and features, is brand-loyal, and avoids risks."},
    'N': {'trait': "Intuition (N)", 'tendency': "Drawn to novelty and innovation. An early adopter who values the concept, story, and aesthetics behind a product."},
    'T': {'trait': "Thinking (T)", 'tendency': "Makes decisions using objective logic. Focuses on price-to-performance ratio and function over form."},
    'F': {'trait': "Feeling (F)", 'tendency': "Makes decisions based on personal values. Influenced by brand ethics, stories, and personal recommendations."},
    'J': {'trait': "Judging (J)", 'tendency': "Prefers a planned, orderly approach. Engages in goal-oriented shopping and favors complete, bundled solutions."},
    'P': {'trait': "Perceiving (P)", 'tendency': "Favors a flexible, spontaneous style. Prone to impulse buys and values versatile, multi-functional products."}
}

# --- MODIFIED: Recommendation function now uses Gemini ---
def generate_recommendations_with_ai(user_name, mbti_type, financial_info, orientation_info):
    if not mbti_type or len(mbti_type) != 4:
        return "Could not generate recommendations due to invalid MBTI type."

    knowledge_base = """## Introversion (I) vs. Extraversion (E): The Social World 🧠
This dimension is about where individuals direct their energy: inward to the world of ideas or outward to the world of people and activities.
Introverts (I) - Depth over Breadth
Behavioral Driver: They are driven by enriching their inner world and engaging in deep, focused activities. They value privacy and substance.
Purchasing Habits: Thorough Research, Utility for Solitude, Long-Term Value.
Example Products: High-fidelity headphones, single-player video games, books, home-comfort items (e.g., ergonomic chair, premium coffee maker).
Extraverts (E) - Breadth over Depth
Behavioral Driver: They are energized by social interaction, new experiences, and being involved in the world around them.
Purchasing Habits: Social Proof & Trends, Experience-Oriented, Appearance & Status.
Example Products: Concert or event tickets, group travel packages, trendy or fashionable apparel, board games, new smartphones with great cameras.
## Sensing (S) vs. Intuition (N): The World of Information ⚙️
This dimension describes how people perceive information: focusing on the concrete reality of what is or the abstract possibilities of what could be.
Sensing (S) - The Practical Realist
Behavioral Driver: They trust what is tangible, real, and proven. They focus on the details and practical application of a product.
Purchasing Habits: Focus on Features & Facts, Brand Loyalty, Risk Aversion.
Example Products: Reliable home appliances from established brands, practical tools(screwdriver, wrench), cars known for reliability, insurance products.
Intuitive (N) - The Innovative Visionary
Behavioral Driver: They are drawn to novelty, innovation, and the "big picture" or concept behind a product.
Purchasing Habits: Early Adopters, Concept over Details, Aesthetic & Symbolism.
Example Products: The latest tech gadgets, electric vehicles, crowdfunded innovative products, I-Phones.
## Thinking (T) vs. Feeling (F): The World of Decisions ❤️
This dimension explains how people make decisions: based on objective logic or on subjective values and impact on people.
Thinking (T) - The Objective Analyst
Behavioral Driver: They make decisions using logical, impersonal analysis. The goal is to find the most effective and logical solution.
Purchasing Habits: Price-to-Performance Ratio, Function Over Form, Skepticism of "Emotional" Marketing.
Example Products: PC components with the best benchmarks and good price, budget smart phones with good specs, tools chosen for pure efficiency.
Feeling (F) - The Empathetic Harmonizer
Behavioral Driver: They make decisions based on their personal values and how the outcome will affect others. Maintaining harmony is key.
Purchasing Habits: Brand Ethics and Story, Personal Recommendations, Aesthetic and Personal Connection.
Example Products: Products that support a personal identity, jewelry, unique and fashionable clothing, a thoughtful personalized gift for a loved one.
## Judging (J) vs. Perceiving (P): The World of Structure 🗓️
This dimension reflects a person's preference for lifestyle and structure: planned and organized or spontaneous and adaptable.
Judging (J) - The Decisive Planner
Behavioral Driver: They prefer a planned, orderly world and seek to have decisions made and settled.
Purchasing Habits: Goal-Oriented Shopping, Less Impulse Buying, Prefer "Complete" Solutions.
Example Products: Bulk purchases from a warehouse store, an automated subscription service for household essentials, a complete matching furniture set, a pre-arranged all-inclusive vacation package.
Perceiving (P) - The Spontaneous Explorer
Behavioral Driver: They prefer a flexible, spontaneous life and enjoy keeping their options open.
Purchasing Habits: Prone to Impulse Buying, Hesitant to Commit, Value Versatility.
Example Products: An item bought from a flash sale, modular furniture that can be rearranged, a multi-purpose gadget like a convertible laptop, versatile clothing items that can be styled in multiple ways."""
    
    recommendation_prompt = f"""
    You are a product recommendation expert. Your task is to give product recommendation, refer to the knowledge base.

    USER PROFILE:
    - Name: {user_name}
    - MBTI Type: {mbti_type}
    - Financial Situation: {financial_info}
    - Sexual Orientation: {orientation_info}

    KNOWLEDGE BASE:
    {knowledge_base}

    INSTRUCTIONS:
    Based on the user's four traits ({mbti_type}) and the knowledge base, generate 8 product recommendations for each trait.

    OUTPUT FORMAT:
    Your response MUST be formatted with each trait on a new line, starting with the trait's letter, a colon, and then a comma-separated list of max 5 product names. Don't suggest long descriptions(A productivity app utilizing AI or innovative algorithms, A stylish yet minimalist desk organizer, A subscription to a magazine focused on future trends or scientific breakthroughs, A speculative fiction novel exploring advanced concepts, An online course on a cutting-edge technology or abstract philosophy, A piece of conceptual art or a unique scientific diagram poster, An innovative sustainable product), see the style of writing in knowledge base example try avoiding things like library card or online apps people generally don't need. Actual physical products with basic description like electric cars(If possible you can suugest a model name with description, like electric cars(Tesla Model 3)) are better.
    For example:
    E: Product description 1 (example product NAME), Product description 2 (example product NAME), Product description 3 (example product NAME), Product description 4 (example product NAME)
    N: Product description 5 (example product NAME), Product description 6 (example product NAME), Product description 7 (example product NAME), Product description 8 (example product NAME)
    F: Product description 9 (example product NAME), Product description 10 (example product NAME), Product description 11 (example product NAME), Product description 12 (example product NAME)
    P: Product description 13 (example product NAME), Product description 14 (example product NAME), Product description 15 (example product NAME), Product description 16 (example product NAME)
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(recommendation_prompt)
        response_text = response.text.strip()
        
        parsed_products = {}
        for line in response_text.split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                letter = parts[0].strip().upper()
                products = parts[1].strip()
                if letter in "ESTJIFNP":
                    parsed_products[letter] = products

        md = f"### 🎁 Personalized Product Recommendations for {st.session_state.user_name} ({mbti_type})\n"
        md += "| personality trait | Expected purchasing behaviour | Product recommendations based on Expected purchasing behaviour and optional details |\n"
        md += "|---|---|---|\n"

        for letter in mbti_type:
            data = RECOMMENDATION_LOGIC.get(letter.upper())
            products_str = parsed_products.get(letter.upper(), "Could not generate.")
            if data:
                md += f"| **{data['trait']}** | {data['tendency']} | {products_str} |\n"
        
        return md

    except Exception as e:
        return f"An unexpected error occurred while generating recommendations with the Gemini API: {e}"

# --- Streamlit App ---
st.set_page_config(page_title="Aura - Your Peer Mentor", page_icon="💖")
st.title("💖 Aura: Your Supportive Peer Mentor")
st.caption("A safe space to chat, powered by Google Gemini and tailored to your personality.")

# --- Initialization & Main App Logic ---
init_db()
if "messages" not in st.session_state: st.session_state.messages = []
if "system_prompt" not in st.session_state: st.session_state.system_prompt = ""
if "chat_started" not in st.session_state: st.session_state.chat_started = False
# ... [rest of your session state initializations remain the same] ...
if "narrative_mode" not in st.session_state: st.session_state.narrative_mode = True
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "mbti_type" not in st.session_state: st.session_state.mbti_type = None
if "mbti_results" not in st.session_state: st.session_state.mbti_results = None
if "financial_info" not in st.session_state: st.session_state.financial_info = ""
if "orientation_info" not in st.session_state: st.session_state.orientation_info = ""
if "recorder_counter" not in st.session_state: st.session_state.recorder_counter = 0
if "last_audio_id" not in st.session_state: st.session_state.last_audio_id = None
if "last_options" not in st.session_state: st.session_state.last_options = []
if "onboarding_step" not in st.session_state: st.session_state.onboarding_step = "get_name"
if "show_recommendations" not in st.session_state: st.session_state.show_recommendations = False


st.sidebar.title("Controls")
st.session_state.narrative_mode = st.sidebar.toggle("Enable Narrative Conversation", value=st.session_state.narrative_mode, help="Aura will suggest replies.")
if st.session_state.chat_started:
    if st.sidebar.button("🎁 Get Product Recommendations"):
        st.session_state.show_recommendations = True
        st.rerun()
if st.sidebar.button("Start New Chat"):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# --- MODIFIED: Aura's response function now uses Gemini ---
def get_aura_response():
    try:
        # Use a more powerful model for nuanced conversation
        model = genai.GenerativeModel(
            model_name='gemini-2.5-pro',
            system_instruction=st.session_state.system_prompt
        )

        # Convert session state messages to the format Gemini expects for history
        # Gemini uses "model" for the assistant's role.
        history = []
        for msg in st.session_state.messages:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            history.append({"role": role, "parts": msg["parts"]})

        # The last message is the new prompt, so we remove it from the history
        # and send it separately.
        if history and history[-1]["role"] == "user":
            latest_prompt = history.pop()["parts"][0]
        else:
            # Should not happen in a normal flow, but as a fallback:
            return "Something went wrong in the conversation flow. Please try again."

        chat = model.start_chat(history=history)
        response = chat.send_message(latest_prompt)
        
        return response.text

    except Exception as e:
        st.error(f"An unexpected error occurred with the Gemini API: {e}")
        return None

# --- Main App Flow (largely unchanged, calls the new Gemini functions) ---

# Onboarding flow
if not st.session_state.chat_started:
    st.session_state.show_recommendations = False
    if st.session_state.onboarding_step == "get_name":
        st.markdown("#### Welcome! I'm Aura.")
        name = st.text_input("First, what should I call you?", key="name_input")
        if st.button("Continue"):
            if name.strip():
                st.session_state.user_name = name.strip()
                existing_user_data = get_user(st.session_state.user_name)
                if existing_user_data:
                    st.session_state.mbti_type, st.session_state.financial_info, st.session_state.orientation_info = existing_user_data
                    st.session_state.mbti_results = generate_placeholder_results(st.session_state.mbti_type)
                    st.session_state.onboarding_step = "final_setup"
                    st.success(f"Welcome back, {st.session_state.user_name}! Loading your profile.")
                else:
                    st.session_state.onboarding_step = "new_user_choice"
                st.rerun()
            else:
                st.warning("Please enter your name.")

    # ... [The rest of your onboarding steps: new_user_choice, take_test, select_type]
    # ... [This code is identical to your original script and can be copied here]
    elif st.session_state.onboarding_step == "new_user_choice":
        st.markdown(f"### Hi, {st.session_state.user_name}! It's nice to meet you.")
        st.markdown("To help me understand you better, how should we determine your personality type?")
        with st.expander("What is MBTI? Click to learn more..."):
            st.markdown("""
            The MBTI was built on the theories of the Swiss psychiatrist Carl Jung. It looks at four key areas:
            * **Where you get your energy:** Introversion (I) or Extraversion (E).
            * **How you process information:** Sensing (S) or Intuition (N).
            * **How you make decisions:** Thinking (T) or Feeling (F).
            * **How you prefer to live:** Judging (J) or Perceiving (P).
            """)
        col1, col2 = st.columns(2)
        if col1.button("Take the Personality Test ✨"):
            st.session_state.onboarding_step = "take_test"
            st.rerun()
        if col2.button("I Already Know My Type 📝"):
            st.session_state.onboarding_step = "select_type"
            st.rerun()
    elif st.session_state.onboarding_step == "take_test":
        st.markdown("##### For each statement, please select the option that feels most like you.")
        with st.form("mbti_form"):
            answers = [st.radio(f"**{i+1}. {q['question']}**", LIKERT_SCALE_OPTIONS, key=f"q_{i}", index=2, horizontal=True) for i, q in enumerate(ADVANCED_MBTI_QUESTIONS)]
            if st.form_submit_button("Calculate My Type"):
                with st.spinner("Analyzing your results..."):
                    scores = calculate_mbti_scores(answers)
                    mbti_type, results_dict = interpret_scores(scores)
                    st.session_state.mbti_type = mbti_type
                    st.session_state.mbti_results = results_dict
                    st.session_state.onboarding_step = "final_setup"
                st.rerun()
    elif st.session_state.onboarding_step == "select_type":
        st.markdown("##### Please select your MBTI type from the list below.")
        mbti_type = st.selectbox("Your MBTI Type:", options=list(MBTI_DESCRIPTIONS.keys()), index=None)
        if st.button("Confirm Type"):
            if mbti_type:
                st.session_state.mbti_type = mbti_type
                st.session_state.mbti_results = generate_placeholder_results(mbti_type)
                st.session_state.onboarding_step = "final_setup"
                st.rerun()
            else:
                st.warning("Please select a type.")

    elif st.session_state.onboarding_step == "final_setup":
        st.success(f"Great! Your personality type is set as **{st.session_state.mbti_type}**.")
        results = st.session_state.mbti_results
        st.subheader("Your Personality Profile")
        col1, col2, col3, col4 = st.columns(4)
        def format_delta(percentage):
            if isinstance(percentage, int):
                return f"{percentage}% Strength"
            return None
        with col1: st.metric(label="Extraversion vs Introversion", value=results['E/I_Letter'], delta=format_delta(results['E/I_Percentage']))
        with col2: st.metric(label="Sensing vs Intuition", value=results['S/N_Letter'], delta=format_delta(results['S/N_Percentage']))
        with col3: st.metric(label="Thinking vs Feeling", value=results['T/F_Letter'], delta=format_delta(results['T/F_Percentage']))
        with col4: st.metric(label="Judging vs Perceiving", value=results['J/P_Letter'], delta=format_delta(results['J/P_Percentage']))
        st.info(MBTI_DESCRIPTIONS[st.session_state.mbti_type])
        st.markdown("---")
        with st.expander("Optional: Share more context for a better chat"):
            financial_info_value = "" if st.session_state.financial_info == "unknown" else st.session_state.financial_info
            orientation_info_value = "" if st.session_state.orientation_info == "unknown" else st.session_state.orientation_info
            financial_info = st.text_input("Financial Situation", value=financial_info_value, key="financial_input")
            orientation_info = st.text_input("Sexual Orientation", value=orientation_info_value, key="orientation_input")
        problem = st.text_area("What's on your mind today?", height=150)
        if st.button("Start Chat with Aura"):
            if problem.strip():
                save_user(st.session_state.user_name, st.session_state.mbti_type, financial_info, orientation_info)
                st.session_state.system_prompt = generate_system_prompt(st.session_state.user_name, st.session_state.mbti_type, financial_info, orientation_info, st.session_state.narrative_mode)
                st.session_state.messages.append({"role": "user", "parts": [problem]})
                st.session_state.chat_started = True
                with st.spinner("Aura is thinking..."):
                    full_response = get_aura_response()
                    if full_response:
                        main_text, options = full_response, []
                        if st.session_state.narrative_mode and "---OPTIONS---" in full_response:
                            try:
                                parts = full_response.split("---OPTIONS---", 1)
                                main_text = parts[0].strip()
                                options_str = parts[1].strip()
                                options = [opt.strip().lstrip('- ') for opt in options_str.split('\n') if opt.strip()]
                            except Exception: pass
                        st.session_state.messages.append({"role": "assistant", "parts": [main_text]})
                        st.session_state.last_options = options
                st.rerun()
            else:
                st.warning("Please share what's on your mind to start the chat.")

# Chat Interface Logic
else:
    # ... [The entire chat interface logic is identical to your original]
    # ... [It will now call the new Gemini-powered functions correctly]
    if st.session_state.get("show_recommendations", False):
        with st.container(border=True):
            st.info("Product ideas based on the user's personality profile. Click 'Back to Chat' to hide.")
            user_data = get_user(st.session_state.user_name)
            if user_data:
                mbti, fin_info, orient_info = user_data
                with st.spinner("🧠 Generating unique recommendations with AI..."):
                    recommendation_md = generate_recommendations_with_ai(st.session_state.user_name, mbti, fin_info, orient_info)
                st.markdown(recommendation_md)
            else:
                st.warning("Could not retrieve user data to generate recommendations.")

            if st.button("⬅️ Back to Chat"):
                st.session_state.show_recommendations = False
                st.rerun()
    else:
        st.success(f"You are now chatting with Aura. Hi, {st.session_state.user_name}! 👋")
        def handle_prompt(prompt_text):
            if not prompt_text or not prompt_text.strip(): return
            st.session_state.messages.append({"role": "user", "parts": [prompt_text]})
            with st.spinner("Aura is thinking..."):
                full_response = get_aura_response()
                if full_response:
                    main_text, options = full_response, []
                    if st.session_state.narrative_mode and "---OPTIONS---" in full_response:
                        try:
                            parts = full_response.split("---OPTIONS---", 1)
                            main_text = parts[0].strip()
                            options_str = parts[1].strip()
                            options = [opt.strip().lstrip('- ') for opt in options_str.split('\n') if opt.strip()]
                        except Exception: pass
                    st.session_state.messages.append({"role": "assistant", "parts": [main_text]})
                    st.session_state.last_options = options
                    st.session_state.recorder_counter += 1
            st.rerun()

        for message in st.session_state.messages:
            role = "assistant" if message["role"] != "user" else "user"
            with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "💖"):
                st.markdown(message["parts"][0])

        if st.session_state.narrative_mode and st.session_state.last_options:
            cols = st.columns(len(st.session_state.last_options))
            for i, option in enumerate(st.session_state.last_options):
                if cols[i].button(option, key=f"option_{i}_{st.session_state.recorder_counter}"):
                    st.session_state.last_options = []
                    handle_prompt(option)

        st.write("Talk to Aura:")
        audio_data = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop Recording", key=f'recorder_{st.session_state.recorder_counter}')
        if audio_data and audio_data['id'] != st.session_state.last_audio_id:
            st.session_state.last_audio_id = audio_data['id']
            with st.spinner("Transcribing your voice..."):
                audio_prompt = transcribe_audio(audio_data['bytes'])
                if audio_prompt: handle_prompt(audio_prompt)

        if text_prompt := st.chat_input("Or type your message here..."):
            handle_prompt(text_prompt)
