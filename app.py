import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from flask_cors import CORS

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Flask App
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)  # Enable CORS for frontend communication

# Initialize LLM securely
llm = ChatGroq(
    temperature=0,
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
)

# Prompt Template
itinerary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful travel assistant. Create a travel itinerary for {city} based on "
            "the user's interests: {interests}. The user has a budget of {budget} INR for {people} people, "
            "traveling from {from_date} to {to_date}. Provide a structured plan including recommended places, "
            "food options, and local experiences. If available, consider the weather: {weather}.",
        ),
        ("human", "Create an itinerary for my trip."),
    ]
)

# Serve HTML Pages
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/generate-itinerary", methods=["GET"])
def itinerary_page():
    return render_template("generate-itinerary.html")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup.html")


# Fetch Weather
def fetch_weather(city, from_date, to_date):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_response = requests.get(geo_url, timeout=5)
        geo_data = geo_response.json()

        if "results" in geo_data and geo_data["results"]:
            lat, lon = geo_data["results"][0]["latitude"], geo_data["results"][0]["longitude"]
            url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={from_date}&end_date={to_date}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
            response = requests.get(url, timeout=5)
            data = response.json()

            if "daily" in data:
                avg_max_temp = round(sum(data["daily"]["temperature_2m_max"]) / len(data["daily"]["temperature_2m_max"]), 1)
                avg_min_temp = round(sum(data["daily"]["temperature_2m_min"]) / len(data["daily"]["temperature_2m_min"]), 1)
                return f"Avg Max Temp: {avg_max_temp}°C, Avg Min Temp: {avg_min_temp}°C"
        return ""
    except:
        return ""

# API Endpoint: Generate Itinerary
@app.route("/api/generate-itinerary", methods=["POST"])
def generate_itinerary():
    data = request.json
    city = data["city"]
    interests = data["interests"]
    budget = data["budget"]
    people = data["people"]
    from_date = data["from_date"]
    to_date = data["to_date"]

    # Fetch weather data
    weather = fetch_weather(city, from_date, to_date)

    # Generate itinerary
    response = llm.invoke(
        itinerary_prompt.format_messages(
            city=city,
            interests=", ".join(interests),
            budget=budget,
            people=people,
            from_date=from_date,
            to_date=to_date,
            weather=weather or "N/A",
        )
    )

    return jsonify({"itinerary": response.content, "weather": weather})

# API Endpoint: Chatbot
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]
    itinerary = data["itinerary"]

    chat_response = llm.invoke(
        f"Previous itinerary: {itinerary}\nUser query: {user_message}"
    )

    return jsonify({"response": chat_response.content})

if __name__ == "__main__":
    print(app.url_map)
    app.run(debug=True)