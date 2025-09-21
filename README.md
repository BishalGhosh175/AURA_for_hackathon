# AURA_for_hackathon
# 💖 Aura: Your Supportive Peer Mentor

Aura is a conversational AI peer mentor designed to be a safe and supportive space for users to share what's on their minds. Powered by Google's Gemini Pro model, Aura listens empathetically and provides responses tailored to the user's personality, using the Myers-Briggs Type Indicator (MBTI) as a guide.

![Aura Screenshot Placeholder](https://user-images.githubusercontent.com/1097257/203233854-f7b247f9-4467-4638-9276-267f8a33a1e9.png)
*A placeholder image. You can replace this by taking a screenshot of your running application.*

---

## ✨ Features

-   **MBTI-Personalized Conversations**: Aura tailors its communication style (e.g., logical vs. feeling-oriented) based on your selected MBTI type.
-   **Voice-to-Text Input**: Speak your thoughts naturally using the built-in microphone recorder.
-   **Narrative Mode**: Aura can suggest follow-up replies to help guide the conversation and keep it flowing smoothly.
-   **Context-Aware Support**: Optionally share your financial situation or sexual orientation for more mindful and relevant advice.
-   **Built-in Crisis Protocol**: Automatically provides a crisis hotline number if a user expresses thoughts of self-harm.
-   **Secure & Private**: Your API key and conversation details are handled securely using Streamlit's secrets management.

---

## 🛠️ Tech Stack

-   **Framework**: Streamlit
-   **Language**: Python
-   **LLM**: Google Gemini 1.5 Pro
-   **Audio Processing**: `streamlit-mic-recorder`, `SpeechRecognition`, `pydub`

---

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

-   Python 3.8 or newer
-   `ffmpeg`: A cross-platform solution to record, convert and stream audio and video. It is required by `pydub`. You can install it using a package manager like Homebrew (`brew install ffmpeg`) on macOS or Chocolatey (`choco install ffmpeg`) on Windows.

### Installation & Setup

1.  **Clone the Repository** (or download the source code):
    ```sh
    git clone [https://github.com/your-username/aura-chatbot.git](https://github.com/your-username/aura-chatbot.git)
    cd aura-chatbot
    ```

2.  **Create a Virtual Environment**:
    It's highly recommended to create a virtual environment to keep dependencies isolated.
    ```sh
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    Install all the required packages using the `requirements.txt` file.
    ```sh
    pip install -r requirements.txt
    ```

4.  **Set Up Your API Key**:
    Aura uses Streamlit's secrets management for the Gemini API Key.
    -   Create a folder named `.streamlit` in your project's root directory.
    -   Inside this folder, create a file named `secrets.toml`.
    -   Add your Gemini API key to this file as shown below:
    ```toml
    # .streamlit/secrets.toml
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    ```

---

## ▶️ How to Run

Once the setup is complete, you can run the Streamlit application with the following command in your terminal:

```sh
streamlit run app.py
