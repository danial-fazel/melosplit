# **MeloSplit: A Group Expense Manager**

MeloSplit is a group expense management application designed to help users easily track, split, and settle shared expenses within groups. It includes AI integration for storytelling about group activities, making expense tracking more engaging.

---

## **Features**
- **User Authentication**: Sign up and log in securely.
- **Group Management**: Create and manage groups with members.
- **Expense Tracking**: Add, split, and settle expenses among group members.
- **Recurring Bills**: Manage recurring expenses with adjustable due dates.
- **AI Storytelling**: Generate engaging stories about group activities using AI.
- **Currency exchanger**: converting currencies most usefull.
- **Settle Up**: Simplify transactions and track payments between group members.

---

## **Tech Stack**
- **Frontend**: KivyMD (Python framework for UI)
- **Backend**: Firebase Realtime Database for data storage
- **AI Integration**: Hugging Face API for storytelling
- **Environment Management**: `.env` files for secure API key storage

---

## **Setup Instructions**

### 1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/MeloSplit.git
cd MeloSplit
```

### 2. **Install Dependencies**
- Make sure you have Python 3.8+ installed.
- Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. **Set Up Firebase**
- Go to the [Firebase Console](https://console.firebase.google.com/).
- Create a new project and set up Realtime Database in **test mode** for development.
- Download the `serviceAccountKey.json` file for admin access and place it in the project root.

#### Update the Firebase Configuration:
- Modify the Firebase database URL in your `app.py`:
```python
firebase_admin.initialize_app(cred, {"databaseURL": "https://your-database.firebaseio.com"})
```

---

### 4. **Configure APIs**
#### Generate a Hugging Face API Key:
- Visit [Hugging Face](https://huggingface.co/).
- Sign up and create a new API key under your account settings.

#### Generate a Currency exchanger API Key:
- Visit [Navasan telegram bot](https://t.me/navasan_contact_bot).
- create a new API key under your account settings.

#### Add Keys to the `.env`:
1. Create a file named `.env` in the project root:
```plaintext
HUGGINGFACE_API_KEY=your_huggingface_api_key
FIREBASE_CREDENTIALS=serviceAccountKey.json
NAVASAN_API_KEY=your_navasan_api_key

```
2. Ensure `.env` is in `.gitignore` to keep it private.

---

### 5. **Run the Application**
```bash
python app.py
```

---

## **Usage Instructions**
1. **Log In or Sign Up**:
   - Use the login screen to access your account or sign up as a new user.

2. **Create Groups**:
   - Add a group and its members.
   - Provide a description for the group for better context.

3. **Add Expenses**:
   - Add individual or recurring expenses.
   - Choose between "Equally", "By Percentage", "By Shares", or "Custom" split types.

4. **Settle Payments**:
   - Simplify transactions using the "Settle Up" feature.
   - Payments can be tracked and settled in the app.

5. **Generate Stories**:
   - Select a story genre and generate AI-driven stories about group activities.

6. **converted currency**:
   - the currencies are converted to most used ones, but you can adjust in the code to get your desirable ones too.

---

## **Project Structure**
```plaintext
MeloSplit/
├── app.py                # Main application file
├── ai.py                 # AI integration with Hugging Face
├── logic.py              # Business logic for group and expense management
├── melosplit.kv          # Kivy UI definitions
├── my_metworkx.py        # modified graph visualization
├── requirements.txt      # Python dependencies
├── serviceAccountKey.json # Firebase admin credentials (not included in GitHub)
├── .env                  # Environment variables (ignored in GitHub)
├── .gitignore            # Git ignore file
└── README.md             # Documentation
```

---

## **Contributing**
Contributions are welcome! Please fork the repository and create a pull request with your changes.

---

## **Security**
- The `.env` file containing sensitive keys is ignored in the repository.
- Firebase rules are configured to restrict access to authenticated users only.

---


## **Contact**
For any questions or suggestions:
- **Email**: Danialfzl832@gmail.com
- **GitHub**: [danial-fazel](https://github.com/danial-fazel)

---
