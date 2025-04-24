from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3, os
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from openai import OpenAI




client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_PATH = "faculty_reviews.db"


nltk.download("vader_lexicon")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "ZULensSeniorProject"
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

sia = SentimentIntensityAnalyzer()

@app.before_request
def redirect_to_www():
    host = request.host
    if host == "zulens.org":
        return redirect("https://www.zulens.org" + request.path, code=301)

# ---------- PAGE ROUTES ----------

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/about-us')
def about():
    return render_template('about-us.html')

@app.route('/contact-us')
def contact():
    return render_template('contact-us.html')

@app.route('/reviews')
def reviews():
    return render_template('reviews.html')

@app.route('/submit-review-page')
def submit_review_page():
    return render_template('submit_review.html')

@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html')

@app.route('/my-reviews')
def my_reviews_page():
    if "user_id" not in session:
        return redirect(url_for("s-login.html"))
    return render_template('my_reviews.html')

@app.route("/student-signup")
def student_signup_page():
    return render_template("s-signup.html")

@app.route("/student-login")
def student_login_page():
    return render_template("s-login.html")

@app.route("/faculty-signup")
def faculty_signup_page():
    return render_template("f-signup.html")

@app.route("/faculty-login")
def faculty_login_page():
    return render_template("f-login.html")

@app.route("/role")
def role_page():
    return render_template("role.html")

@app.route("/faculty/dashboard")
def faculty_dashboard():
    if "user_id" not in session or session.get("role") != "faculty":
        return redirect(url_for("f-login.html"))
    return render_template("faculty_dashboard.html")


# Email configuration (update with your real info)
EMAIL_SENDER = "zulensorg@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587

# ---------- USER AUTH ----------
def send_confirmation_email(to_email, username):
    subject = "Welcome to ZULens!"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>🎉 Welcome to ZULens, {username}!</h2>
        <p>Thank you for signing up to ZULens – your voice matters.</p>
        <p>We’re excited to have you as part of the community!</p>
        <br>
        <p>Cheers,<br>ZULens Team</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email sending failed:", e)


@app.route('/student-signup', methods=['POST'])
def signup_student():
    data = request.get_json()
    email = data.get("email", "").strip()
    student_id = data.get("student_id", "").strip()
    password = data.get("password", "").strip()
    role = "student"

    # Validate inputs
    if not email or not student_id or not password or len(student_id) != 9:
        return jsonify({"error": "Please provide a valid email, 9-digit student ID, and password."}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Email already registered."}), 409

        # Insert student
        cursor.execute("""
            INSERT INTO users (name, email, password, student_id, role)
            VALUES (?, ?, ?, ?, ?)
        """, (None, email, password, student_id, role))

        conn.commit()
        conn.close()

        # Send confirmation email (use email as username placeholder)
        send_confirmation_email(email, email)

        return jsonify({"message": "Account created successfully!"}), 200

    except Exception as e:
        print("Signup Error:", e)
        return jsonify({"error": "Server error during signup."}), 500

@app.route("/faculty-signup", methods=["POST"])
def signup_faculty():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Email already registered"}), 409

        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (name, email, password, "faculty"))

        conn.commit()
        conn.close()

        return jsonify({"message": "Faculty account created!"}), 200

    except Exception as e:
        print("Faculty signup error:", e)
        return jsonify({"error": "Server error during signup"}), 500

@app.route("/login-user", methods=["POST"])
def login_user():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, name, student_id FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_id, role, fullname, student_id = user
        session["user_id"] = user_id
        session["email"] = email
        session["role"] = role
        session["username"] = fullname if role == "faculty" else email
        session["student_id"] = student_id if role == "student" else None

        if role == "faculty":
            return jsonify({"message": "Faculty login successful", "redirect": "/faculty-dashboard"}), 200
        else:
            return jsonify({"message": "Student login successful", "redirect": "/my-reviews"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/faculty-login", methods=["POST"])
def faculty_login():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE email = ? AND password = ? AND role = 'faculty'", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        session["username"] = user[1]
        session["role"] = "faculty"
        session["email"] = email
        return jsonify({"message": "Login successful", "redirect": "/faculty-dashboard"}), 200
    else:
        return jsonify({"error": "Invalid credentials or not a faculty account"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out", "redirect": "/"})

# ---------- FACULTY DASHBOARD ROUTES ----------

@app.route("/faculty/reviews")
def get_faculty_reviews():
    faculty_fullname = session.get("faculty_fullname")
    if not faculty_fullname:
        return jsonify([])

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, course, instructor, rating, review, sentiment, summary, flagged, user_id, grade 
        FROM reviews 
        WHERE instructor = ?
    """, (faculty_fullname,))
    rows = cursor.fetchall()
    conn.close()

    reviews = []
    for row in rows:
        student_id_display = "Hidden"
        # You can fetch student ID from users table if you wish, here we're skipping it for privacy
        reviews.append({
            "id": row[0],
            "course": row[1],
            "instructor": row[2],
            "rating": row[3],
            "review": row[4],
            "sentiment": row[5],
            "summary": row[6],
            "flagged": bool(row[7]),
            "student_id": student_id_display,
            "grade": row[9]
        })

    return jsonify(reviews)


# ---------- TONE CHECK ENDPOINT ----------

@app.route("/check-tone", methods=["POST"])
def check_tone():
    review = request.json.get("review", "")
    sentiment_score = sia.polarity_scores(review)
    compound = sentiment_score["compound"]

    warning = None
    if compound <= -0.4:
        warning = "⚠️ Your review seems harsh. Consider rewording to sound more constructive."

    return jsonify({"warning": warning})

# ---------- FACULTY REVIEWS ----------
@app.route("/faculty/get-my-reviews", methods=["GET"])
def faculty_get_reviews():
    if "user_id" not in session or session.get("role") != "faculty":
        return jsonify({"error": "Unauthorized"}), 401

    faculty_fullname = session.get("fullname")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, student_id, course, rating, review, sentiment, summary
        FROM reviews
        WHERE instructor = ?
    """, (faculty_fullname,))
    rows = cursor.fetchall()
    conn.close()

    reviews = [{
        "id": row[0],
        "student_id": row[1],
        "course": row[2],
        "rating": row[3],
        "review": row[4],
        "sentiment": row[5],
        "summary": row[6]
    } for row in rows]

    return jsonify(reviews), 200

@app.route("/faculty/reveal-grade", methods=["POST"])
def reveal_grade():
    if "user_id" not in session or session.get("role") != "faculty":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    review_id = data.get("review_id")
    grade = data.get("grade", "").strip().upper()

    if not review_id or grade not in ["A", "B", "C", "D", "F"]:
        return jsonify({"error": "Invalid input"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET revealed_grade = ? WHERE id = ?", (grade, review_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Grade revealed"}), 200

@app.route("/faculty/report-review", methods=["POST"])
def report_review():
    if "user_id" not in session or session.get("role") != "faculty":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    review_id = data.get("review_id")
    reason = data.get("reason", "").strip()

    if not review_id or not reason:
        return jsonify({"error": "Missing review or reason"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO review_reports (review_id, faculty_id, reason)
        VALUES (?, ?, ?)
    """, (review_id, session["user_id"], reason))
    conn.commit()
    conn.close()

    return jsonify({"message": "Review reported"}), 200

@app.route("/faculty/notifications", methods=["POST"])
def toggle_notifications():
    user_id = session.get("user_id")
    if not user_id or session.get("role") != "faculty":
        return jsonify({"error": "Unauthorized"}), 403

    enabled = request.json.get("enabled", True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE faculty SET email_notifications = ? WHERE id = ?", (int(enabled), user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Updated"})


# ---------- REVIEWS ----------

@app.route('/submit-review', methods=['POST'])
def submit_review():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    course = data.get("course", "").replace(" ", "").replace("-", "").upper()
    raw_instructor = data.get("instructor", "").strip()
    instructor = "Prof. " + " ".join([part.capitalize() for part in raw_instructor.split()])
    review = data.get("review", "").strip()
    rating = int(data.get("rating", 3))

    if not course or not instructor or not review:
        return jsonify({"error": "Missing fields"}), 400

    prompt = f"""
    Analyze the following student review and return:
    1. The overall sentiment as Positive, Negative, or Neutral.
    2. A short summary of the review mentioning the course and instructor name.

    Course ID: {course}
    Instructor: {instructor}
    Rating: {rating} / 5
    Review: {review}

    Respond in this JSON format:
    {{"sentiment": "...", "summary": "..."}}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        sentiment_data = json.loads(content)
        sentiment = sentiment_data["sentiment"]
        summary = sentiment_data["summary"]
    except Exception as e:
        print("GPT error:", e)
        sentiment = "Neutral"
        summary = "Summary unavailable due to error."

    flagged = 1 if sentiment.lower() == "negative" and rating <= 2 else 0

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reviews (course, instructor, rating, review, sentiment, summary, flagged, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (course, instructor, rating, review, sentiment, summary, flagged, user_id))
    conn.commit()
    conn.close()
    
    # Notify faculty if the name matches and notifications are enabled
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email, email_notifications FROM faculty WHERE fullname = ?", (instructor,))
    faculty = cursor.fetchone()
    conn.close()

    if faculty and faculty[1] == 1:  # notifications are on
        faculty_email = faculty[0]
        subject = "🔔 New Review Submitted on ZULens"
        body = f"""Hello {instructor},

    A new anonymous review mentioning you has been submitted on ZULens.

    Please log in to your Faculty Dashboard to view it:
    🔗 https://www.zulens.org/faculty/dashboard

    -- ZULens Team
    """

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = EMAIL_SENDER
            msg["To"] = faculty_email

            server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, faculty_email, msg.as_string())
            server.quit()
        except Exception as e:
            print("❌ Faculty email failed:", e)

    return jsonify({
        "message": "Review submitted successfully",
        "sentiment": sentiment,
        "summary": summary,
        "flagged": bool(flagged)
    })



@app.route('/get-reviews', methods=['GET'])
def get_reviews():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, course, instructor, rating, review, sentiment, summary, flagged FROM reviews")
    rows = cursor.fetchall()
    conn.close()

    reviews = []
    for row in rows:
        reviews.append({
            "id": row[0],
            "course": row[1],
            "instructor": row[2],
            "rating": row[3],
            "review": row[4],
            "sentiment": row[5],
            "summary": row[6],
            "flagged": bool(row[7])
        })

    return jsonify(reviews), 200

@app.route('/get-my-reviews', methods=['GET'])
def get_my_reviews():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, course, instructor, rating, review, sentiment, summary, flagged 
        FROM reviews WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    reviews = [{
        "id": row[0],
        "course": row[1],
        "instructor": row[2],
        "rating": row[3],
        "review": row[4],
        "sentiment": row[5],
        "summary": row[6],
        "flagged": bool(row[7])
    } for row in rows]

    return jsonify(reviews)

@app.route("/delete-review-by-id", methods=["POST"])
def delete_review_by_id():
    user_id = session.get("user_id")
    review_id = request.json.get("review_id")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE id = ? AND user_id = ?", (review_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Review deleted"}), 200

@app.route("/update-review", methods=["POST"])
def update_review():
    data = request.json
    review_id = data.get("review_id")
    new_text = data.get("new_text", "").strip()
    new_course = data.get("new_course", "").strip()
    new_instructor = data.get("new_instructor", "").strip()

    if not review_id or not new_text or not new_course or not new_instructor:
        return jsonify({"error": "Missing fields"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT sentiment, summary, flagged FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Review not found"}), 404

    existing_sentiment, existing_summary, existing_flagged = row

    cursor.execute("""
        UPDATE reviews 
        SET review = ?, course = ?, instructor = ?, sentiment = ?, summary = ?, flagged = ?
        WHERE id = ?
    """, (new_text, new_course, new_instructor, existing_sentiment, existing_summary, existing_flagged, review_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Review updated"}), 200

@app.route("/review-stats")
def review_stats():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE sentiment = 'Positive'")
    positive = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE sentiment = 'Negative'")
    negative = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE sentiment = 'Neutral'")
    neutral = cursor.fetchone()[0]

    conn.close()
    return jsonify({
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral
    })


# ---------- CHATBOT ----------
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip().lower()

    # Fetch reviews
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT course, instructor, rating, sentiment, review FROM reviews")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"reply": "Sorry, no reviews available yet."})

    
    review_data = [
        f"Course: {row[0]}, Instructor: {row[1]}, Rating: {row[2]}/5, Sentiment: {row[3]}, Review: {row[4]}"
        for row in rows
    ]
    joined_data = "\n".join(review_data)

    # Sending GPT a prompt of what is needed
    prompt = f"""
You are a helpful university course advisor for ZULens.

Student asked: "{user_message}"

You have access to the following reviews:
{joined_data}

Based on this data:
- Understand that course prefixes like "CHE" mean Chemistry, "MTH" is Math, "SEC" is Security, etc.
- Recommend or explain courses/instructors that match what the student asked (like "easy chemistry course", "strict professor", etc.).
- Reference real review info when possible.
- Respond conversationally, as if you’re helping a peer.

Return only a helpful reply — no JSON formatting.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatbot error:", e)
        reply = "Something went wrong while trying to help. Please try again later."

    return jsonify({"reply": reply})

# ---------- INIT DB ----------

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            student_id TEXT,
            role TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT,
            instructor TEXT,
            rating INTEGER,
            review TEXT,
            sentiment TEXT,
            summary TEXT,
            flagged INTEGER DEFAULT 0,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER,
            faculty_id INTEGER,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(review_id) REFERENCES reviews(id),
            FOREIGN KEY(faculty_id) REFERENCES users(id)
        );
    """)

    # Add revealed_grade column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE reviews ADD COLUMN revealed_grade TEXT DEFAULT NULL;")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)