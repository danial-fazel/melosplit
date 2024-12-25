from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
import re
from kivymd.toast import toast
from logic import Graph  
from kivymd.uix.boxlayout import MDBoxLayout

# Firebase imports
import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate("melosplit-firebase.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://melosplit-default-rtdb.firebaseio.com/"
})

def add_user_to_firebase(email, name):
    uid = email  # Using email as UID
    ref = db.reference("/users/")
    ref.child(uid).set({"name": name, "email": email})

def get_user_groups_from_firebase(uid):
    groups_ref = db.reference("/groups/")
    groups = groups_ref.get()
    user_groups = []
    if groups:
        for group_id, group_data in groups.items():
            if uid in group_data.get("members", []):
                user_groups.append(group_data.get("name", "Unknown Group"))
    return user_groups

def local_data():
    """saving data in offline mode, uploadin when got online"""
    pass 

def local_loggedin():
    """not logging in again in same device"""
    pass 


class LoginScreen(MDScreen):
    def login(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()
        
        # Convert email to a safe key
        safe_email = re.sub(r'[.#$/\[\]]', '_', email)

        if not email or not password:
            self.show_error("Please fill in all fields.")
            return

        # Check Firebase for the user
        user_ref = db.reference(f"/users/{safe_email}")
        user_data = user_ref.get()

        if user_data and user_data.get("password") == password:
            App.get_running_app().user_uid = safe_email  # Store UID for future use
            App.get_running_app().root.current = "group_manager"
        else:
            self.show_error("Invalid email or password.")

    def show_error(self, message):
        dialog = MDDialog(title="Error", text=message, buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())])
        dialog.open()

class SignupScreen(MDScreen):
    def signup(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()

        # Convert email to a safe key
        safe_email = re.sub(r'[.#$/\[\]]', '_', email)

        if not email or not password:
            self.show_error("Please fill in all fields.")
            return

        # Check if user already exists
        user_ref = db.reference(f"/users/{safe_email}")
        if user_ref.get():
            self.show_error("User already exists. Please log in.")
            return

        # Save the new user
        user_ref.set({
            "email": email,
            "password": password,
        })

        App.get_running_app().root.current = "login"  # Redirect to login

    def show_error(self, message):
        dialog = MDDialog(title="Error", text=message, buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())])
        dialog.open()


class GroupManagerScreen(Screen):
    def on_enter(self):
        """Load groups when the screen is displayed."""
        self.load_groups()

    def load_groups(self):
        """Load user groups dynamically into the group list."""
        user_uid = App.get_running_app().user_uid
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        groups = user_groups_ref.get() or {}

        group_list = self.ids.group_list
        group_list.clear_widgets()
        for group_name in groups:
            group_list.add_widget(
                MDRaisedButton(
                    text=group_name,
                    on_release=lambda x=group_name: self.go_to_group_screen(x),
                )
            )


    def go_to_group_screen(self, group_name):
        """Navigate to the selected group's screen."""
        App.get_running_app().group_name = group_name
        self.manager.current = "group_screen"

class AddGroupScreen(Screen):
    def next_step(self):
        """Validate group name and number of members, then navigate to member input screen."""
        group_name = self.ids.group_name_input.text.strip()
        num_members = self.ids.num_members_input.text.strip()

        if not group_name:
            toast("Please enter a group name.")
            return
        if not num_members.isdigit() or int(num_members) <= 0:
            toast("Please enter a valid number of members.")
            return

        # Pass data to the next screen
        self.manager.get_screen("member_inputs_screen").setup_inputs(
            group_name, int(num_members)
        )
        self.manager.current = "member_inputs_screen"


class MemberTemplate(MDBoxLayout):
    pass


class MemberInputsScreen(Screen):
    def setup_inputs(self, group_name, num_members):
        """Prepare inputs for member names and emails."""
        self.group_name = group_name  # Store the group name
        member_list = self.ids.member_inputs_list
        member_list.clear_widgets()  # Clear existing widgets

        # Add input fields for each member
        for _ in range(num_members):
            member_widget = MemberTemplate()  # Create a new instance of MemberTemplate
            member_list.add_widget(member_widget)

    def submit_group(self):
        """Add group to Firebase, validate emails, and initialize the graph."""
        group_name = self.group_name
        members = []

        # Collect member details from inputs
        for child in self.ids.member_inputs_list.children:
            name = child.ids.member_name.text.strip()
            email = child.ids.member_email.text.strip()

            if name:
                if email:
                    # Validate email and fetch UID
                    safe_email = re.sub(r"[.#$/\[\]]", "_", email)
                    user_ref = db.reference(f"/users/{safe_email}")
                    user_data = user_ref.get()
                    if user_data:
                        members.append({"uid": safe_email, "name": name})
                    else:
                        toast(f"User with email {email} does not exist.")
                        return
                else:
                    members.append({"uid": None, "name": name})

        if not members:
            toast("Please enter at least one member.")
            return

        # Save the group to Firebase
        user_uid = App.get_running_app().user_uid
        group_ref = db.reference(f"groups/{group_name}")
        group_data = {
            "members": {m["uid"] or m["name"]: m["name"] for m in members},
        }
        group_ref.set(group_data)

        # Add the group to the user's groups
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        user_groups_ref.update({group_name: "Member"})

        # Initialize the group graph
        group_graph = Graph()
        for member in members:
            if member["uid"]:
                group_graph.add_transaction(member["uid"], user_uid, 0)

        toast(f"Group '{group_name}' created.")
        self.manager.current = "group_manager"


class GroupScreen(Screen):
    def on_enter(self):
        group_name = App.get_running_app().group_name
        self.ids.group_title.text = f"Group: {group_name}"

    def transactions_history(self):
        pass
        # group_name = App.get_running_app().group_name
        # group_ref = db.reference(f"groups/{group_name}")
        # group_data = group_ref.get()
        # if group_data:
        #     members = group_data["members"]
        #     for member in members:
        #         if member["uid"]:
        #             user_ref = db.reference(f"/users/{member['uid']}")
        #             user_data = user_ref.get()
        #             if user_data:
        #                 self.ids.transactions_history.append_widget(TransactionHistoryWidget(user_data["name"], user_data["uid"]
        #                                                                                      , group_name))
        #             else:
        #                 self.ids.transactions_history.append_widget(TransactionHistoryWidget(member["name"], None, group_name))

    def members_summary(self):
        pass

    def add_expences(self):
        pass

    def settle_ups(Self):
        pass


class MemberSummaryScreen(Screen):
    """the list of members with their net balances and a button to a screen to show the graph visualisation"""
    pass 

class AddExpencesScreen(Screen):
    """choosing different modes of split and the payer and the people in share and the amount and the category and also maybe a note, then using the logic in graph for calculating stuff and add in the database"""
    """also an optinal feature to access a site for different currencies global"""
    pass

class SettleUpScreen(Screen):
    """in the main screen using minimize cash flow func of the logic to dispaly the simplified transactions and a key to add expence as in payer and the payee for settling debts"""
    pass

class UserProfileScreen():
    """calculating and showing the user net balance in all their groups,the ability to change password and log out"""
    pass


class MyScreenManager(ScreenManager):
    pass

class MeloSplit(MDApp):
    user_uid = "test_user_uid"  # Temporary for testing

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        return MyScreenManager()

if __name__ == "__main__":
    MeloSplit().run()

