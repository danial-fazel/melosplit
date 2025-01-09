from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
import re
from kivymd.toast import toast
from logic import Graph, Group, Bill
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty,NumericProperty
from datetime import datetime
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDDatePicker
from collections import defaultdict
import networkx as nx
from currency import *
import json
import os
from ai import AIService
from kivy.lang import Builder 
from kivy.core.text import LabelBase 
from kivymd.app import MDApp 
from kivymd.theming import ThemeManager
from decouple import config
from ai import AIService
# Firebase imports
import firebase_admin
from firebase_admin import credentials, db
# Initialize Firebase

cred_path = config("FIREBASE_CREDENTIALS")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {"databaseURL": "https://melosplit-default-rtdb.firebaseio.com/"})

# Initialize the AI service with our API key


api_key = config("HUGGINGFACE_API_KEY")

ai_service = AIService(api_key)

def add_user_to_firebase(email, name):
    at_sign = email.find('@')
    email = email[:at_sign]
    uid = re.sub(r'[.#$/\[\]]', '_', email) # remove special characters
    ref = db.reference("/users/")
    ref.child(email).set({"{uid}": name})

# def get_user_groups_from_firebase(uid):
#     groups_ref = db.reference("/groups/")
#     groups = groups_ref.get()
#     user_groups = []
#     if groups:
#         for group_id, group_data in groups.items():
#             if uid in group_data.get("members", []):
#                 user_groups.append(group_data.get("name", "Unknown Group"))
#     return user_groups

def local_data():
    """saving data in offline mode, uploadin when got online"""
    pass 

def local_loggedin():
    """not logging in again in same device"""
    pass 

the_group = None  # Global variable to store the active Group instance
chand = fetch_currency_data()

def save_group_to_firebase():
    """Save the current the_group instance to Firebase."""
    global the_group
    if not the_group:
        raise ValueError("The group is not initialized.")

    # Convert the nested defaultdict to a standard dictionary for saving
    edges_dict = {
        payer: dict(payees)
        for payer, payees in the_group.graph.edges.items()
    }

    # Save all group data back to Firebase
    group_ref = db.reference(f"groups/{the_group.name}")
    group_ref.update({
        "members": the_group.members or {},
        "category": the_group.get_category(),
        "description": the_group.discript(),
        "edges": edges_dict or {},
        # "transactions": the_group.graph.transactions or [],
        "recurring_bills": list(the_group.graph.recurring_bills),
        "category_totals": dict(the_group.graph.category_totals),
    })


class LoginScreen(MDScreen):
    def login(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()

        # Convert email to a safe key
        at_sign = email.find('@')
        safe_email = email[:at_sign]
        safe_email = re.sub(r'[.#$/\[\]]', '_', safe_email)

        if not email or not password:
            self.show_error("Please fill in all fields.")
            return

        # Check Firebase for the user
        user_ref = db.reference(f"/users/{safe_email}")
        user_data = user_ref.get()

        if user_data and user_data.get("password") == password:
            App.get_running_app().user_email = email
            App.get_running_app().user_uid = safe_email  # Store UID for future use

            # Save session locally
            self.save_user_session(safe_email, email)

            App.get_running_app().root.current = "group_manager"
        else:
            self.show_error("Invalid email or password.")

    def save_user_session(self, user_uid, user_email):
        """Save the logged-in user's session locally."""
        session_data = {"user_uid": user_uid, "user_email": user_email}
        with open("user_session.json", "w") as session_file:
            json.dump(session_data, session_file)

    def show_error(self, message):
        dialog = MDDialog(title="Error", text=message, buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())])
        dialog.open()


class SignupScreen(MDScreen):
    def signup(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()

        # Convert email to a safe key
        at_sign = email.find('@')
        safe_email = email[:at_sign]
        safe_email = re.sub(r'[.#$/\[\]]', '_', safe_email)

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

        App.get_running_app().user_email = email
        App.get_running_app().user_uid = safe_email

        # Save session locally
        self.save_user_session(safe_email, email)

        App.get_running_app().root.current = "group_manager"

    def save_user_session(self, user_uid, user_email):
        """Save the signed-up user's session locally."""
        session_data = {"user_uid": user_uid, "user_email": user_email}
        with open("user_session.json", "w") as session_file:
            json.dump(session_data, session_file)

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
        self.update_user_groups_in_firebase(user_uid)
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        groups = user_groups_ref.get() or {}

        group_list = self.ids.group_list  # The MDList widget
        group_list.clear_widgets()

        for group_name in groups:
            # Add each group as a list item with a clickable action
            item = OneLineListItem(
                text=group_name,
                on_release=lambda btn, group=group_name: self.go_to_group_screen(group),
            )
            group_list.add_widget(item)

    def update_user_groups_in_firebase(self, member_uid):
        """
        Find all groups that a specific member belongs to and update them
        in the Firebase path users/{member_uid}/groups.
        """
        groups_ref = db.reference("/groups")
        groups = groups_ref.get()  # Fetch all groups

        if not groups:
            return

        user_groups_path = f"/users/{member_uid}/groups"
        user_groups_ref = db.reference(user_groups_path)

        # Prepare a dictionary to update the user's groups
        user_groups = {}

        # Loop through all groups
        for group_name, group_data in groups.items():  # Use the key as the group name
            members = group_data.get("members", {})
            if member_uid in members:
                user_groups[group_name] = group_name  # Use the group key itself as the name

        # Update the user's group list in Firebase
        user_groups_ref.set(user_groups)

    def go_to_group_screen(self, group_name):
        """Navigate to the selected group's screen and initialize the_group."""
        global the_group

        # Fetch group data from Firebase
        group_data_ref = db.reference(f"groups/{group_name}")
        group_data = group_data_ref.get()

        if not group_data:
            toast(f"Group {group_name} not found!")
            return

        # Load edges (nested dictionary) from Firebase or use an empty structure if absent
        edges = group_data.get("edges", {})
        edges = defaultdict(lambda: defaultdict(float), {
            payer: defaultdict(float, payees)
            for payer, payees in edges.items()
        })

        # Initialize the global Group instance
        the_group = Group(
            name=group_name,
            members=group_data.get("members", {}),
            edges=edges,
            recurring_bills=list(group_data.get("recurring_bills", [])),
            category_totals=defaultdict(float, group_data.get("category_totals", {})),
        )

        App.get_running_app().group_name = group_name
        self.manager.current = "group_screen"
    def open_delete_group_dialog(self):
        """Open the GroupDialog to select groups for deletion."""
        user_uid = App.get_running_app().user_uid
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        groups = user_groups_ref.get() or {}

        def handle_selected_groups(selected_groups):
            self.delete_selected_groups(selected_groups)

        self.group_dialog = GroupDialog(groups=groups.keys(), on_submit=handle_selected_groups)
        self.group_dialog.open()

    def delete_selected_groups(self, selected_groups):
        """Delete the selected groups from Firebase."""
        if not selected_groups:
            toast("No groups selected for deletion.")
            return

        groups_ref = db.reference("/groups")
        user_uid = App.get_running_app().user_uid
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        
        for group_name in selected_groups:
            group_ref = db.reference(f"groups/{group_name}")
            group_data = group_ref.get()        
            admin_data = group_data.get("admin")
            
            if App.get_running_app().user_uid != admin_data:
                toast("Only Admin can remove members")
                return
            # Remove group data
            group_ref = groups_ref.child(group_name)
            group_ref.delete()

            # Remove group from user's groups
            user_groups_ref.child(group_name).delete()

        toast(f"Deleted {len(selected_groups)} groups successfully.")
        self.load_groups()  # Refresh the group list



class AddGroupScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.category_items = [
            {"text": "Food", "viewclass": "OneLineListItem", "on_release": lambda x="Food": self.set_category(x)},
            {"text": "Transport", "viewclass": "OneLineListItem", "on_release": lambda x="Transport": self.set_category(x)},
            {"text": "Utilities", "viewclass": "OneLineListItem", "on_release": lambda x="Utilities": self.set_category(x)},
            {"text": "Miscellaneous", "viewclass": "OneLineListItem", "on_release": lambda x="Miscellaneous": self.set_category(x)},
        ]

        self.category_items_menu = MDDropdownMenu(items=self.category_items, width_mult=4)

    def open_category_menu(self, button):
        """Open category menu safely."""
        if not self.category_items_menu.parent:
            self.category_items_menu.caller = button
            self.category_items_menu.open()

    def set_category(self, value):
        self.ids.category_input.text = value
        self.category_items_menu.dismiss()

    def next_step(self):
        """Validate group name and number of members, then navigate to member input screen."""
        group_name = self.ids.group_name_input.text.strip()
        num_members = self.ids.num_members_input.text.strip()
        description = self.ids.description_input.text.strip()
        category = self.ids.category_input.text.strip()

        if not group_name:
            toast("Please enter a group name.")
            return
        if not num_members.isdigit() or int(num_members) <= 1:
            toast("Please enter a valid number of members.")
            return

        # Pass data to the next screen
        self.manager.get_screen("member_inputs_screen").setup_inputs(
            group_name, int(num_members)
        )

        global the_group
        the_group = Group(group_name)
        the_group.discript(description)
        the_group.get_category(category)
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
            if _ == 0:  # For the first member
                member_widget.ids.member_name.text = App.get_running_app().user_uid ##
                member_widget.ids.member_email.text = App.get_running_app().user_email ##


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
                    email = re.sub(r'[.#$/\[\]]', '_', email)###
                    member_uid = email.split('@')[0] ##
                    # user_ref = db.reference(f"/users/{member_uid}")
                    # user_data = user_ref.get()
                    # if user_data:
                    members.append({"uid": member_uid, "name": name})  ##
                    # else:
                    #     toast(f"User with email {email} does not exist.")
                    #     return
                else:
                    members.append({"uid": None, "name": name})

        if len(members) < 2:
            toast("A group must have 2 members at least.")  ##
            return

        global the_group
        for member in members:
            the_group.add_member(member["name"])

        # Save the group to Firebase
        user_uid = App.get_running_app().user_uid
        group_ref = db.reference(f"groups/{group_name}")
        members_data = {
            "members": {m["uid"] or m["name"]: m["name"] for m in members},
        }#TODO: mark the fake uids
        group_ref.set(members_data)

        admin_data = {
            "admin": user_uid,
        }
        group_ref.update(admin_data)###admin 

        # Add the group to the user's groups;
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        user_groups_ref.update({group_name: 0})  ##
        # and to the registered members' groups:
        for member in members:
            if member['uid']:
                member_ref = db.reference(f"/users/{member['uid']}")
                member_data = member_ref.get()
                if member_data:
                    member_groups_ref = db.reference(f"/users/{member['uid']}/groups")
                    member_groups_ref.update({group_name: 0})


        # current_users_list_ref = db.reference(f"users")
        # for member in members:
        #     if member["uid"]:
        #         for uid in dict(current_users_list_ref):
        #             if member["uid"] == uid:
        #                 member_groups_ref = db.reference(f"users/{member}/groups")
        #                 member_groups_ref.update({group_name: 0})

        # # Initialize the group graph
        # the_group = Group(group_name, members_data)  ##
        # for member in members:
        #     member_id = member["uid"] or member["name"]  # Use UID if available, otherwise use the name
        #     if member_id:
        #         the_group.graph.add_transaction(member_id, user_uid, 0)  ## This stuff commented.

        toast(f"Group '{group_name}' created.")
        self.manager.current = "group_manager"


class GroupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.categorized_view = False  # Track current view mode

    def on_enter(self):
        """Set group title and load transaction history when entering the screen."""
        group_name = App.get_running_app().group_name
        self.ids.group_title.text = f"Group: {group_name}"
        self.show_normal_transactions()

    def toggle_transaction_view(self):
        """Switch between categorized and normal transaction view."""
        if self.categorized_view:
            self.show_normal_transactions()
            self.ids.toggle_view_button.text = "Show Categorized"
        else:
            self.categorized_transactions()
            self.ids.toggle_view_button.text = "Show All"
        self.categorized_view = not self.categorized_view

    def show_normal_transactions(self):
        """Display all transactions without categorization."""
        group_name = App.get_running_app().group_name
        global the_group
        members = the_group.members

        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()

        for transaction in reversed(list(transactions.values())):
            uid = transaction.get('payer')
            name = members.get(uid, "Unknown Payer")
            transactions_history.add_widget(
                MDLabel(
                    text=f"{name} paid {transaction.get('amount')} thousand Tomans for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                    font_size=dp(14),
                    size_hint_y=None,
                    height=dp(30),
                )
            )


    def categorized_transactions(self):
        """Fetch and display categorized transactions."""
        group_name = App.get_running_app().group_name
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}
        global the_group
        members = the_group.members

        # Categorize transactions
        categorized = {}
        for transaction_id, transaction in transactions.items():
            category = transaction.get("category", "Uncategorized")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(transaction)

        # Update UI
        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()

        for category, transactions in categorized.items():
            # Add category header
            transactions_history.add_widget(
                MDLabel(
                    text=f"[b]{category}[/b]",
                    markup=True,
                    font_style="H6",
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            # Add transactions under the category
            for transaction in reversed(transactions):
                uid = transaction.get('payer')
                name = members.get(uid, "Unknown Payer")
                transactions_history.add_widget(
                    MDLabel(
                        text=f"{name} paid {transaction.get('amount')} thousand Tomans for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                        font_size=dp(14),
                        size_hint_y=None,
                        height=dp(30),
                    )
                )

    def open_date_picker(self, target):
        """Open date picker for start or end date."""
        date_picker = MDDatePicker()
        date_picker.bind(on_save=lambda instance, value, _: self.set_date(value, target))
        date_picker.open()

    def set_date(self, date, target):
        """Set the selected start or end date."""
        if target == "start":
            self.start_date = date
            toast(f"Start date set to {date}")
        elif target == "end":
            self.end_date = date
            toast(f"End date set to {date}")

    def filter_transactions_by_timeline(self):
        """Filter transactions based on the selected timeline."""
        if not hasattr(self, "start_date") or not hasattr(self, "end_date"):
            toast("Please select both start and end dates.")
            return

        group_name = App.get_running_app().group_name        
        global the_group
        members = the_group.members
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        filtered = []
        for transaction in transactions.values():
            try:
                transaction_date = datetime.strptime(transaction.get("date"), "%Y-%m-%d %H:%M:%S").date()
                if self.start_date <= transaction_date <= self.end_date:
                    filtered.append(transaction)
            except ValueError as e:
                toast(f"Invalid date format in transaction: {e}")
                continue

        # Display filtered transactions
        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()
        for transaction in filtered:
            uid = transaction.get('payer')
            name = members.get(uid, "Unknown Payer")
            transactions_history.add_widget(
                MDLabel(
                    text=f"{name} paid {transaction.get('amount')} thousand Tomans for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                    font_size=dp(14),
                    size_hint_y=None,
                    height=dp(30),
                )
            )

    def open_sort_menu(self):
        """Open a menu for sorting transactions."""
        menu_items = [
            {"text": "By Date", "on_release": lambda x="date": self.sort_transactions(x)},
            {"text": "By Amount", "on_release": lambda x="amount": self.sort_transactions(x)},
        ]
        self.sort_menu = MDDropdownMenu(caller=self.ids.toggle_view_button, items=menu_items, width_mult=4)
        self.sort_menu.open()

    def sort_transactions(self, criterion):
        """Sort transactions by the selected criterion."""
        group_name = App.get_running_app().group_name
        global the_group
        members = the_group.members
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        # Sort transactions
        if criterion == "date":
            sorted_transactions = sorted(
                transactions.values(),
                key=lambda x: datetime.strptime(x.get("date"), "%Y-%m-%d %H:%M:%S"),
            )
        elif criterion == "amount":
            sorted_transactions = sorted(transactions.values(), key=lambda x: float(x.get("amount", 0)))

        # Update UI
        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()
        for transaction in reversed(sorted_transactions):
            uid = transaction.get('payer')
            name = members.get(uid, "Unknown Payer")
            transactions_history.add_widget(
                MDLabel(
                    text=f"{name} paid {transaction.get('amount')} thousand Tomans for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                    font_size=dp(14),
                    size_hint_y=None,
                    height=dp(30),
                )
            )

        self.sort_menu.dismiss()
    def generate_story(self):
        """Open a dialog to let the user choose a genre and then generate a story."""
        genres = ["Scary", "Funny", "Mysterious", "Mixed", "Random"]

        # Create a dialog with buttons for each genre
        genre_buttons = [
            MDRaisedButton(
                text=genre,
                on_release=lambda btn,x=genre: self.on_genre_selected(x)
            )
            for genre in genres
        ]

        self.genre_dialog = MDDialog(
            title="Choose a Story Genre",
            type="custom",
            buttons=genre_buttons,
        )
        self.genre_dialog.open()

    def on_genre_selected(self, genre):
        """Handle the genre selection and generate a story."""
        self.genre_dialog.dismiss()  # Close the dialog

        # Fetch group data from Firebase
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        if not group_data:
            toast("Failed to fetch group data.")
            return

        # Extract relevant details
        group_description = group_data.get("description", "No description provided.")
        members = group_data.get("members", {})  # {uid: name}
        transactions = group_data.get("transactions", [])  # List of transaction dicts

        # Create the prompt
        prompt = ai_service.create_prompt(
            group_name, group_description, members, transactions, genre
        )

        # Send the prompt to AI and handle the response
        story = ai_service.send_request(prompt)
        print(story)
        if story:
            self.show_story(story)
        else:
            toast("Failed to generate story.")

    def show_story(self, story):
        """Display the AI-generated story in a dialog."""
        dialog = MDDialog(
            title="Generated Story",
            text=story,
            buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()


class TransactionHistoryWidget(MDBoxLayout):
    payer = StringProperty()
    participants = StringProperty()
    amount = StringProperty()
    description = StringProperty()
    date = StringProperty()


class MemberSummaryScreen(Screen):
    add_member_dialog = None
    remove_member_dialog = None

    def on_enter(self):
        """Populate the screen with member data when the screen is entered."""
        self.populate_member_summary()

    def populate_member_summary(self):
        """Get the group summary and display the member balances."""
        # Get the group summary
        # group_name = App.get_running_app().group_name
        # group = db.reference(f"groups/{group_name}")

        global the_group
        summary = the_group.get_summary()
        balances = the_group.get_balances()

        # print(the_group.graph.visualize_graph())

        # Clear existing content
        self.ids.member_list.clear_widgets()

        # Add each member's information
        for member, balance in balances.items():
            member_summary = f"{member}:\n Net Balance: {balance:.2f}"
            contribution = summary["per_member_contributions"].get(member, 0)
            member_summary += f"\n Contribution: {contribution:.2f}"

            # Create a label for the member's data and add it to the list
            self.ids.member_list.add_widget(
                MDLabel(text=member_summary, theme_text_color="Primary", size_hint_y=None, height="40dp", halign='center')
            )
            self.ids.member_list.add_widget(
                MDLabel(text="\n\n\n", theme_text_color="Primary", size_hint_y=None, height="40dp", halign='center')
            )

        # Display total expenses
        total_expenses = summary["total_expenses"]
        self.ids.total_expenses_label.text = f"Total Expenses: {total_expenses:.2f} thousand Tomans"

        # Optional: Add category breakdown
        category_summary = summary["category_summary"]
        self.ids.category_summary_label.text = "Category Summary: " + ", ".join(
            [f"{category}: {amount:.2f}" for category, amount in category_summary.items()]
        )

        print(dict(the_group.graph.edges)) # Just checking the graph
        print(dict(the_group.members))

    def open_add_member_dialog(self):
        """Open a dialog to input new member details."""
        if not self.add_member_dialog:
            self.add_member_dialog = MDDialog(
                title="Add Member",
                type="custom",
                content_cls=MDBoxLayout(
                    MDTextField(hint_text="Member Name", id="member_name", text=""),
                    MDTextField(hint_text="Member Email (Optional)", id="member_email"),
                    orientation="vertical",
                    spacing="10dp",
                    size_hint_y=None,
                    height="150dp",
                ),
                buttons=[
                    MDRaisedButton(text="Cancel", on_release=lambda x: self.add_member_dialog.dismiss()),
                    MDRaisedButton(text="Add", on_release=self.add_member),
                ],
            )
        else:
            # Clear the input fields
            self.add_member_dialog.content_cls.ids.member_name.text = ""
            self.add_member_dialog.content_cls.ids.member_email.text = ""
        self.add_member_dialog.open()

    def add_member(self, *args):
        """Add a member to the group."""
        member_name = self.add_member_dialog.content_cls.ids.member_name.text.strip()
        member_email = self.add_member_dialog.content_cls.ids.member_email.text.strip()

        if not member_name:
            toast("Member name is required.")
            return

        # Use email to create UID or default to the name
        member_uid = member_email.split('@')[0] if member_email else member_name #TODO

        global the_group
        the_group.add_member(member_name, member_uid)
        save_group_to_firebase()

        # Refresh UI
        self.populate_member_summary()
        toast(f"Member '{member_name}' added successfully.")
        self.add_member_dialog.dismiss()

    def open_remove_member_dialog(self):
        """Open a dialog to select members to remove."""
        global the_group
        members = the_group.members

        # Create the dialog content dynamically
        participants = {uid: name for uid, name in members.items()}
        self.remove_member_dialog = MembersDialog(participants, self.update_selected_members, "Remove")
        self.remove_member_dialog.open()

    def update_selected_members(self, selected_members):
        """Update the internal state with selected members for removal."""
        self.selected_members_to_remove = selected_members
        self.remove_members()

    def remove_members(self, *args):
        """Remove selected members from the group."""
        global the_group
        selected_members = self.selected_members_to_remove

        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        if not selected_members:
            toast("No members selected for removal.")
            return
        
        admin_data = group_data.get("admin")
        print(admin_data)
        if App.get_running_app().user_uid != admin_data:
            toast("Only Admin can remove members")
            return

        for uid in selected_members:
            the_group.remove_member(uid)

        save_group_to_firebase()

        # Refresh UI
        self.populate_member_summary()
        toast("Selected members removed successfully.")
        self.remove_member_dialog.dismiss()

    def go_back(self):
        """Navigate back to the GroupScreen."""
        self.manager.current = "group_screen"

    def add_expense(self):
        """Navigate to AddExpenseScreen."""
        self.manager.current = "add_expense_screen"

    def settle_up(self):
        """Navigate to SettleUpScreen."""
        self.manager.current = "settle_up_screen"


class AddExpenseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.currency_menu = None
        self.selected_currency = "irtt"  # Default currency

        self.split_type_items = [
            {"text": "Equally", "viewclass": "OneLineListItem", "on_release": lambda x="Equally": self.set_split_type(x)},
            {"text": "By Percentage", "viewclass": "OneLineListItem", "on_release": lambda x="By Percentage": self.set_split_type(x)},
            {"text": "By Shares", "viewclass": "OneLineListItem", "on_release": lambda x="By Shares": self.set_split_type(x)},
            {"text": "Custom", "viewclass": "OneLineListItem", "on_release": lambda x="Custom": self.set_split_type(x)},
        ]

        self.category_items = [
            {"text": "Food", "viewclass": "OneLineListItem", "on_release": lambda x="Food": self.set_category(x)},
            {"text": "Transport", "viewclass": "OneLineListItem", "on_release": lambda x="Transport": self.set_category(x)},
            {"text": "Utilities", "viewclass": "OneLineListItem", "on_release": lambda x="Utilities": self.set_category(x)},
            {"text": "Miscellaneous", "viewclass": "OneLineListItem", "on_release": lambda x="Miscellaneous": self.set_category(x)},
        ]

        self.split_type_menu = MDDropdownMenu(items=self.split_type_items, width_mult=4)
        self.category_menu = MDDropdownMenu(items=self.category_items, width_mult=4)

        self.participants_dialog = None  # To manage the participants dialog
        self.selected_participants = set()

    def open_payer_dropdown(self, button):
        """Open a dropdown for selecting the payer."""
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        if not group_data or "members" not in group_data:
            toast("No members available in this group.")
            return

        participants = group_data["members"]  # {uid: name} mapping

        dropdown_items = [
            {
                "viewclass": "OneLineListItem",
                "text": name,
                "on_release": lambda x=uid: self.set_payer(x),
            }
            for uid, name in participants.items()
        ]

        self.payer_dropdown_menu = MDDropdownMenu(
            items=dropdown_items,
            width_mult=4,
        )
        if not self.payer_dropdown_menu.parent:
            self.payer_dropdown_menu.caller = button
            self.payer_dropdown_menu.open()

    def set_payer(self, uid):
        """Set the selected payer and update the UI."""
        self.payer_dropdown_menu.dismiss()  # Close the dropdown menu
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        members = group_ref.child("members").get()

        if members and uid in members:
            self.selected_payer = uid  # Store the payer UID
            # self.ids.payer_name.text = members[uid]  # Display the payer name in the UI
        else:
            toast("Invalid payer selected.")

    def open_currency_menu(self, instance):
        if self.currency_menu and self.currency_menu.parent:
            self.currency_menu.dismiss()  # Ensure the previous menu is dismissed

        currencies = ["irtt", "usd", "eur", "gbp"]  # supported currencies
        menu_items = [
            {"text": currency.upper(), "on_release": lambda x=currency: self.set_currency(x)}
            for currency in currencies
        ]
        self.currency_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.currency_menu.open()

    def set_currency(self, currency):
        self.selected_currency = currency
        self.ids.currency_field.text = currency.upper()
        self.currency_menu.dismiss()


    def open_split_type_menu(self, button):
        """Open split type menu safely."""
        if not self.split_type_menu.parent:
            self.split_type_menu.caller = button
            self.split_type_menu.open()

    def set_split_type(self, value):
        self.ids.split_type.text = value
        self.split_type_menu.dismiss()

    def open_split_type_menu(self, button):
        """Open split type menu safely."""
        if not self.split_type_menu.parent:
            self.split_type_menu.caller = button
            self.split_type_menu.open()

    def open_category_menu(self, button):
        """Open category menu safely."""
        if not self.category_menu.parent:
            self.category_menu.caller = button
            self.category_menu.open()

    def set_category(self, value):
        self.ids.category.text = value
        self.category_menu.dismiss()

    def open_participant_dialog(self):
        """Open participant dialog with input fields based on split type."""
        split_type = self.ids.split_type.text  # Determine the split type
        group_name = App.get_running_app().group_name  # Get the current group name
        group_ref = db.reference(f"groups/{group_name}")  # Reference to the group in Firebase
        group_data = group_ref.get()

        if not group_data or "members" not in group_data:
            toast("No participants available in this group.")
            return

        participants = group_data["members"]  # {uid: name} mapping

        def on_submit(selected):
            """Callback function to update the selected participants."""
            self.selected_participants = selected  # Store selected UIDs and values
            participant_names = [participants[uid] for uid in selected.keys()]  # Convert UIDs to names for display
            self.ids.selected_participants_label.text = ", ".join(participant_names)  # Update UI with names

        # Open the dialog with participants and submit callback
        self.dialog = ParticipantDialog(participants, on_submit, split_type)
        self.dialog.open()



    def update_selected_participants(self, selected_participants):
        """Update the UI and internal state with selected participants and values."""
        self.selected_participants = selected_participants
        participant_text = ", ".join(
            f"{name} ({value})" for name, value in selected_participants.items()
        )
        self.ids.selected_participants_label.text = (
            f"Selected: {participant_text}" if participant_text else "None"
        )

    def add_expense(self):
        """Add expense using logic and save it to Firebase."""
        payer = self.selected_payer
        amount = self.ids.amount.text.strip()
        split_type = self.ids.split_type.text.strip()
        category = self.ids.category.text.strip()
        description = self.ids.description.text.strip()
        selected_currency = self.selected_currency

        if not payer or not amount or not split_type or not category:
            self.ids.error_label.text = "All fields except description are required!"
            return

        if not self.selected_participants:
            self.ids.error_label.text = "At least one participant must be selected!"
            return

        # Convert amount to default currency (IRTT)
        try:
            converted_amount = int(convert_currency(amount, selected_currency, chand, "irtt")) #TODO rond??
        except ValueError as e:
            toast(f"Currency conversion error: {str(e)}")
            return
        except TypeError as e:
            # print(e)
            toast(f"Currency conversion type error: {str(e)}")
            return

        # Convert amount to float
        try:
            amount = float(converted_amount)
        except ValueError:
            self.ids.error_label.text = "Invalid amount!"
            return

        # Prepare custom splits or percentages for specific modes
        custom_splits = self.selected_participants

        if split_type == "By Shares" and (sum(custom_splits.values()) <= 0 or isinstance(sum(custom_splits.values()), int)):
            self.ids.error_label.text = "Shares must be positive integers!"
            return
        if split_type == "By Percentage" and abs(sum(custom_splits.values()) - 100) > 0.01:
            self.ids.error_label.text = "Total percentage must equal 100!"
            return
        if split_type == "Custom" and abs(sum(custom_splits.values()) - amount) > 0.01:
            self.ids.error_label.text = "Custom amounts must sum to the total amount!"
            return


        # Initialize or load the group graph
        global the_group
        group_name = App.get_running_app().group_name
        group_graph = the_group.graph

        # Add the bill to the graph
        group_graph.add_bill(
            Bill(
                payer=payer,
                amount=amount,
                participants=list(self.selected_participants),
                category=category,
            ),
            split_type=split_type,
            custom_splits=custom_splits,
        )
        # print(f"\nA:\n{dict(group_graph.edges)}")
        # print(f"\n\nB:\n{dict(group_graph.category_totals)}\n")
        # print(the_group.members)

        save_group_to_firebase()

        # Save transaction to Firebase
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transaction_ref.push({
            "payer": payer,
            "participants": list(self.selected_participants),
            "amount": amount,
            "category": category,
            "split_type": split_type,
            "custom_splits": custom_splits,
            "description": description,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        # Clear inputs and provide feedback
        self.clear_inputs()
        toast("Expense added successfully.")
        self.manager.current = "group_screen"

    # def get_group_graph(self, group_name):
    #     """Retrieve or initialize the graph for a specific group."""
    #     group_ref = db.reference(f"groups/{group_name}/graph")
    #     group_graph = Graph()
    #     return group_graph

    def clear_inputs(self):
        """Clear all input fields."""
        self.selected_payer = ""
        self.ids.amount.text = ""
        self.ids.split_type.text = ""
        self.ids.category.text = ""
        self.ids.description.text = ""
        self.selected_participants.clear()

    def highlight_selected_participants(self):
        pass


from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import OneLineListItem, MDList
from kivy.uix.scrollview import ScrollView

class ParticipantDialog:
    def __init__(self, participants, on_submit, split_type="Equally"):
        """
        :param participants: Dictionary of participant UIDs to names.
        :param on_submit: Callback function to handle selected participants.
        :param split_type: The split type (e.g., "Equally", "By Percentage", "By Shares", "Custom").
        """
        self.participants = participants  # {uid: name}
        self.split_type = split_type
        self.selected_participants = {}  # Store selected participants as {uid: value}
        self.on_submit = on_submit

        # Create dialog content
        self.dialog_content = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self.dialog_content.height = len(participants) * 60 + 20

        scroll = ScrollView()
        list_view = MDList()

        # Add participant inputs or checkboxes
        for uid, name in participants.items():
            item = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=60)

            if split_type == "Equally":
                # For "Equally", use checkboxes
                checkbox = MDCheckbox(size_hint_x=0.1)
                checkbox.bind(active=lambda _, active, uid=uid: self.toggle_selection(uid, active))
                item.add_widget(checkbox)
            else:
                # For other split types, use input fields
                input_field = MDTextField(
                    hint_text=self.get_hint_text(),
                    size_hint_x=0.4,
                    halign="center",
                    pos_hint={"center_y": 0.5},  # Adjust alignment
                )
                item.add_widget(input_field)
                self.selected_participants[uid] = {"selected": True, "value": input_field}

            label = MDLabel(text=name, size_hint_x=0.6 if split_type != "Equally" else 0.9)
            item.add_widget(label)

            list_view.add_widget(item)

        scroll.add_widget(list_view)
        self.dialog_content.add_widget(scroll)

        # Create dialog
        self.dialog = MDDialog(
            title=f"Select Participants ({split_type})",
            type="custom",
            content_cls=self.dialog_content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss),
                MDRaisedButton(text="OK", on_release=self.submit),
            ],
        )

    def open(self):
        """Open the dialog."""
        self.dialog.open()

    def dismiss(self, *args):
        """Close the dialog."""
        self.dialog.dismiss()

    def toggle_selection(self, uid, active):
        """Toggle participant selection."""
        if self.split_type == "Equally":
            if active:
                self.selected_participants[uid] = 0  # Default value for equal split
            else:
                self.selected_participants.pop(uid, None)

    def submit(self, *args):
        """Submit selected participants and values."""
        if self.split_type == "Equally":
            selected = {uid: 0 for uid in self.selected_participants.keys()}  # Equal split
        else:
            selected = {
                uid: float(field["value"].text) if field["value"].text.strip() else 0
                for uid, field in self.selected_participants.items()
            }

        self.on_submit(selected)  # Callback with UIDs and values
        self.dismiss()

    def get_hint_text(self):
        """Return appropriate hint text based on the split type."""
        if self.split_type == "By Shares":
            return "Enter shares"
        elif self.split_type == "By Percentage":
            return "Enter %"
        elif self.split_type == "Custom":
            return "Enter amount"
        else:
            return ""



class MembersDialog:
    def __init__(self, participants, on_submit, action="Select", split_type="Equally"):
        """
        :param participants: Dictionary of participant IDs and names.
        :param on_submit: Callback function to handle selected participants.
        :param action: The action type (e.g., "Select", "Remove").
        :param split_type: The split type for expenses (e.g., "Equally", "Custom").
        """
        self.participants = participants
        self.action = action
        self.split_type = split_type
        self.selected_participants = {}
        self.on_submit = on_submit

        # Create dialog content
        self.dialog_content = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self.dialog_content.height = len(participants) * 60 + 20

        scroll = ScrollView()
        list_view = MDList()

        # Add participant inputs or checkboxes
        for uid, name in participants.items():
            item = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=60)

            if split_type == "Equally" or action == "Remove":
                # For "Equally" or "Remove", use checkboxes only
                checkbox = MDCheckbox(size_hint_x=0.1)
                checkbox.bind(active=lambda _, active, uid=uid: self.toggle_selection(active, uid))
                item.add_widget(checkbox)
            else:
                # For other split types, use input fields only
                input_field = MDTextField(
                    hint_text=self.get_hint_text(),
                    size_hint_x=0.4,
                    halign="center",
                    pos_hint={"center_y": 0.5},  # Adjust alignment
                )
                item.add_widget(input_field)
                self.selected_participants[uid] = {"selected": True, "value": input_field}

            label = MDLabel(text=name, size_hint_x=0.6 if split_type != "Equally" else 0.9)
            item.add_widget(label)

            list_view.add_widget(item)

        scroll.add_widget(list_view)
        self.dialog_content.add_widget(scroll)

        # Create dialog
        self.dialog = MDDialog(
            title=f"{self.action} Participants",
            type="custom",
            content_cls=self.dialog_content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss),
                MDRaisedButton(text="OK", on_release=self.submit),
            ],
        )

    def open(self):
        """Open the dialog."""
        self.dialog.open()

    def dismiss(self, *args):
        """Close the dialog."""
        self.dialog.dismiss()

    def toggle_selection(self, active, uid):
        """Toggle participant selection."""
        if active:
            self.selected_participants[uid] = True
        else:
            self.selected_participants.pop(uid, None)

    def submit(self, *args):
        """Submit selected participants."""
        self.on_submit(self.selected_participants)
        self.dismiss()

    def get_hint_text(self):
        """Get hint text based on split type."""
        if self.split_type == "Custom":
            return "Amount"
        elif self.split_type == "By Percentage":
            return "Percentage"
        elif self.split_type == "By Shares":
            return "Shares"
        return ""

class GroupDialog:
    def __init__(self, groups, on_submit, action="Delete"):
        """
        :param groups: Dictionary of group names.
        :param on_submit: Callback function to handle selected groups.
        :param action: The action type (e.g., "Delete").
        """
        self.groups = groups
        self.action = action
        self.selected_groups = set()  # To store selected group names
        self.on_submit = on_submit

        # Create dialog content
        self.dialog_content = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self.dialog_content.height = len(groups) * 60 + 20

        scroll = ScrollView()
        list_view = MDList()

        # Add group checkboxes
        for group_name in groups:
            item = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=60)

            # Add a checkbox for each group
            checkbox = MDCheckbox(size_hint_x=0.1)
            checkbox.bind(active=lambda _, active, group_name=group_name: self.toggle_selection(active, group_name))
            item.add_widget(checkbox)

            # Add group name label
            label = MDLabel(text=group_name, size_hint_x=0.9)
            item.add_widget(label)

            list_view.add_widget(item)

        scroll.add_widget(list_view)
        self.dialog_content.add_widget(scroll)

        # Create the dialog
        self.dialog = MDDialog(
            title=f"{self.action} Groups",
            type="custom",
            content_cls=self.dialog_content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss),
                MDRaisedButton(text="OK", on_release=self.submit),
            ],
        )

    def toggle_selection(self, active, group_name):
        """Toggle group selection."""
        if active:
            self.selected_groups.add(group_name)
        else:
            self.selected_groups.discard(group_name)

    def open(self):
        """Open the dialog."""
        self.dialog.open()

    def dismiss(self, *args):
        """Close the dialog."""
        self.dialog.dismiss()

    def submit(self, *args):
        """Submit selected groups."""
        self.on_submit(self.selected_groups)
        self.dismiss()

class AddRecurringBillScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.next_due_date = None
        self.selected_participants = {}
        self.currency_menu = None
        self.selected_currency = "irtt"  # Default currency

    def open_frequency_menu(self, instance):
        """Open dropdown for frequency selection."""
        menu_items = [
            {"text": "Weekly", "on_release": lambda x="Weekly": self.set_frequency(x)},
            {"text": "Monthly", "on_release": lambda x="Monthly": self.set_frequency(x)},
            {"text": "Yearly", "on_release": lambda x="Yearly": self.set_frequency(x)},
        ]
        self.frequency_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.frequency_menu.open()

    def set_frequency(self, frequency):
        """Set the selected frequency."""
        self.ids.frequency.text = frequency
        self.frequency_menu.dismiss()

    def open_currency_menu(self, instance):
        if self.currency_menu and self.currency_menu.parent:
            self.currency_menu.dismiss()  # Ensure the previous menu is dismissed

        currencies = ["irtt", "usd", "eur", "gbp"]  # Example supported currencies
        menu_items = [
            {"text": currency.upper(), "on_release": lambda x=currency: self.set_currency(x)}
            for currency in currencies
        ]
        self.currency_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.currency_menu.open()

    def set_currency(self, currency):
        self.selected_currency = currency
        self.ids.currency_field.text = currency.upper()
        self.currency_menu.dismiss()
    def open_split_type_menu(self, instance):
        """Open dropdown for split type selection."""
        menu_items = [
            {"text": "Equally", "on_release": lambda x="Equally": self.set_split_type(x)},
            {"text": "By Percentage", "on_release": lambda x="By Percentage": self.set_split_type(x)},
            {"text": "By Shares", "on_release": lambda x="By Shares": self.set_split_type(x)},
            {"text": "Custom", "on_release": lambda x="Custom": self.set_split_type(x)},
        ]
        self.split_type_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.split_type_menu.open()

    def set_split_type(self, split_type):
        """Set the selected split type."""
        self.ids.split_type.text = split_type
        self.split_type_menu.dismiss()

    def open_payer_dropdown(self, button):
        """Open a dropdown for selecting the payer."""
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        if not group_data or "members" not in group_data:
            toast("No members available in this group.")
            return

        participants = group_data["members"]  # {uid: name} mapping

        dropdown_items = [
            {
                "viewclass": "OneLineListItem",
                "text": name,
                "on_release": lambda x=uid: self.set_payer(x),
            }
            for uid, name in participants.items()
        ]

        self.payer_dropdown_menu = MDDropdownMenu(
            items=dropdown_items,
            width_mult=4,
        )
        if not self.payer_dropdown_menu.parent:
            self.payer_dropdown_menu.caller = button
            self.payer_dropdown_menu.open()

    def set_payer(self, uid):
        """Set the selected payer and update the UI."""
        self.payer_dropdown_menu.dismiss()  # Close the dropdown menu
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        members = group_ref.child("members").get()

        if members and uid in members:
            self.selected_payer = uid  # Store the payer UID
            # self.ids.payer_name.text = members[uid]  # Display the payer name in the UI
        else:
            toast("Invalid payer selected.")

    def open_participant_dialog(self):
        """Open participant selection dialog."""
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        if not group_data or "members" not in group_data:
            toast("No participants available in this group.")
            return

        participants = group_data["members"]
        self.dialog = ParticipantDialog(participants, self.update_selected_participants, self.ids.split_type.text)
        self.dialog.open()

    def update_selected_participants(self, selected_participants):
        """Update the UI and internal state with selected participants."""
        self.selected_participants = selected_participants
        participant_text = ", ".join(
            f"{name} ({value})" for name, value in selected_participants.items()
        )
        self.ids.selected_participants_label.text = (
            f"Selected: {participant_text}" if participant_text else "None"
        )

    def open_date_picker(self):
        """Open date picker for next due date."""
        date_picker = MDDatePicker()
        date_picker.bind(on_save=self.set_date)
        date_picker.open()

    def set_date(self, instance, value, _):
        """Set the selected date."""
        self.next_due_date = value
        self.ids.selected_date_label.text = f"Next Due Date: {value}"

    def add_recurring_bill(self):
        """Add recurring bill using logic and save it to Firebase."""
        payer = self.selected_payer
        amount = self.ids.amount.text.strip()
        split_type = self.ids.split_type.text.strip()
        frequency = self.ids.frequency.text.strip()
        description = self.ids.description.text.strip()
        selected_currency = self.selected_currency

        if not payer or not amount or not split_type or not frequency or not self.next_due_date:
            toast("Please fill in all required fields.")
            return

        if not self.selected_participants:
            toast("At least one participant must be selected!")
            return

        # Convert amount to float
        try:
            amount = float(amount)
        except ValueError:
            toast("Invalid amount!")
            return
        
        custom_splits = self.selected_participants

        if split_type == "By Shares" and sum(custom_splits.values()) <= 0:
            self.ids.error_label.text = "Total shares must be greater than zero!"
            return
        if split_type == "By Percentage" and abs(sum(custom_splits.values()) - 100) > 0.01:
            self.ids.error_label.text = "Total percentage must equal 100!"
            return
        if split_type == "Custom" and abs(sum(custom_splits.values()) - amount) > 0.01:
            self.ids.error_label.text = "Custom amounts must sum to the total amount!"
            return
        

        # Convert amount to default currency (IRTT)
        try:
            amount = convert_currency(amount, selected_currency, chand, "irtt") #TODO rond??
        except ValueError as e:
            toast(f"Currency conversion error: {str(e)}")
            return
        except TypeError as e:
            toast(f"Currency conversion type error: {str(e)}")
            return

        # Use converted_amount for further processing
        # toast(f"Expense added: {converted_amount} IRTT")

        # Logic for saving to Firebase or app data structure...


        # Initialize or load the group graph
        global the_group
        group_name = App.get_running_app().group_name
        group_graph = the_group.graph
        
        # Add the recurring bill
        group_graph.add_recurring_bill(
            Bill(
                payer=payer,
                amount=amount,
                participants=list(self.selected_participants),
                category="",  # TODO: Add category logic if needed
                frequency=frequency,
                next_due_date=str(self.next_due_date),
            )
        )

        group_graph.add_bill(
            Bill(
                payer=payer,
                amount=amount,
                participants=list(self.selected_participants),
                category="",
            ),
            split_type=split_type,
            custom_splits=custom_splits,
        )

        # Save the recurring bill to Firebase
        recurring_bills_ref = db.reference(f"groups/{group_name}/recurring_bills")
        recurring_bills_ref.push({
            "payer": payer,
            "amount": amount,
            "frequency": frequency,
            "next_due_date": str(self.next_due_date),
            "participants": self.selected_participants,
            "split_type": split_type,
            "description": description,
        })

        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transaction_ref.push({
            "payer": payer,
            "participants": self.selected_participants,
            "amount": amount,
            "description": description,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        toast("Recurring bill added successfully.")
        self.manager.current = "group_screen"

    def prefill_form(self, group_name, bill):
        """Pre-fill the form with recurring bill details."""
        self.selected_payer = ", ".join(bill.payer if isinstance(bill.payer, list) else [bill.payer])
        self.ids.amount.text = str(bill.amount)
        self.ids.split_type.text = bill.split_type
        self.ids.frequency.text = bill.frequency
        self.ids.selected_date_label.text = f"Next Due Date: {bill.next_due_date.strftime('%Y-%m-%d')}"
        self.group_name = group_name  # Track the group name for saving changes
        App.get_running_app().group_name = self.group_name
        self.selected_participants = {p: 0 for p in bill.participants}



from functools import partial

class SettleUpScreen(Screen):
    def on_enter(self):
        """Generate and display the settle-up transactions when the screen is opened."""
        global the_group
        group_graph = the_group.graph  # Always fetch the latest graph data
        members = the_group.members
        # Get simplified transactions
        simplified_transactions = group_graph.minimize_cash_flow()
        self.simplified_transactions = simplified_transactions
        # Display the transactions
        settle_up_list = self.ids.settle_up_list
        settle_up_list.clear_widgets()

        if not simplified_transactions:
            settle_up_list.add_widget(
                MDLabel(
                    text="All debts are settled!",
                    halign="center",
                    font_style="H6",
                    size_hint_y=None,
                    height=dp(40),
                )
            )
        else:
            for payer_uid, payee_uid, amount in simplified_transactions:
                payer_name = members.get(payer_uid, "Unknown Payeer")
                payee_name = members.get(payee_uid, "Unknown Payee")
                # Add transaction details and button inline
                item = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(10))
                item.add_widget(
                    MDLabel(
                        text=f"{payee_name} owes {payer_name} {amount:.2f} thousand Tomans\n(or {convert_currency(amount, 'irtt', chand, 'usd'):.2f} USD/ {convert_currency(amount, 'irtt', chand, 'eur'):.2f} EUR/ {convert_currency(amount, 'irtt', chand, 'gbp'):.2f} GBP)",
                        size_hint_x=0.7,
                    )
                )
                # Use functools.partial to bind arguments correctly
                settle_button = MDRaisedButton(
                    text="Settle Payment",
                    size_hint_x=0.3,
                    on_release=lambda btn,p=payer_uid, py=payee_uid, a=amount: self.settle_payment(p, py, a),
                )
                item.add_widget(settle_button)
                settle_up_list.add_widget(item)

    def settle_payment(self, payer, payee, amount):
        """Navigate to the settle payment screen with transaction details."""
        app = App.get_running_app()
        app.root.current = "settle_payment_screen"

        settle_payment_screen = self.manager.get_screen("settle_payment_screen")
        settle_payment_screen.prefill(payer, payee, amount)
        
        # Navigate to the "Add Recurring Bill" screen
        self.manager.current = "settle_payment_screen"

class SettlePaymentScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.currency_menu = None
        self.selected_currency = "irtt"

    def open_currency_menu(self, instance):
        if self.currency_menu and self.currency_menu.parent:
            self.currency_menu.dismiss()  # Ensure the previous menu is dismissed

        currencies = ["irtt", "usd", "eur", "gbp"]  # Example supported currencies
        menu_items = [
            {"text": currency.upper(), "on_release": lambda x=currency: self.set_currency(x)}
            for currency in currencies
        ]
        self.currency_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.currency_menu.open()

    def set_currency(self, currency):
        self.selected_currency = currency
        self.ids.currency_field.text = currency.upper()
        self.currency_menu.dismiss()


    def prefill(self, payer, payee, amount):
        """Pre-fill the payment form with transaction details."""
        self.payer = payer
        self.payee = payee
        self.amount= amount
        app = App.get_running_app()
        global the_group
        members = the_group.members  # {uid: name}
        payer_name = members.get(payer, "Unknown Payer")
        payee_name = members.get(payee, "Unknown Payee")

        self.ids.payer_name.text = payer_name
        self.ids.payee_name.text = payee_name
        self.ids.amount.text = f"{amount:.2f}"

    def confirm_payment(self):
        """Record the payment in the group graph and Firebase."""
        app = App.get_running_app()
        current_user = app.user_uid  # Assuming user_uid is stored in the app instance
        payee_uid = self.payee

        if current_user != self.payer:
            toast("Only the payee can confirm this payment.")
            return

        payer = self.payer
        payee = payee_uid
        amount = self.ids.amount.text.strip()

        global the_group
        group_graph = the_group.graph

        if not payer or not payee or not amount:
            toast("All fields are required!")
            return
        try:
            amount = int(convert_currency(float(amount), self.selected_currency, chand, 'irtt')) #TODO rond??
        except ValueError:
            toast("Invalid amount!")
            return
        # Update group graph
        group_name = app.group_name
        group_graph.add_transaction(payer, payee, -amount)  # Negative amount to indicate payment

        # Record the payment in Firebase
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transaction_ref.push({
            "payer": payer,
            "participants": [payee],
            "amount": -amount,
            "description": "Settle Payment",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        toast("Payment recorded successfully.")
        self.manager.current = "settle_up_screen"


# from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
# import matplotlib.pyplot as plt

class GraphVisualizationScreen(Screen):
    def on_enter(self):
        """Render the graph when the screen is displayed."""
        global the_group  # Access the global group data
        the_group.graph.visualize_graph(the_group.name)
        image_widget = self.ids.graph_image
        image_widget.source = "graph.png"  # Update this path dynamically if needed
        image_widget.reload()  # Force reload of the image




class UserProfileScreen(Screen):
    """calculating and showing the user net balance in all their groups,the ability to change password and log out"""
    def on_enter(self):
        """Update the user's net balance and check for notifications when entering the screen."""
        self.update_net_balance()

    def update_net_balance(self):
        """Calculate and display the user's net balance across all groups."""
        user_uid = App.get_running_app().user_uid
        total_balance = 0.0

        # Fetch all groups the user belongs to
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        groups = user_groups_ref.get() or {}

        for group_name in groups:
            # Fetch group data
            group_ref = db.reference(f"groups/{group_name}")
            group_data = group_ref.get()
            if not group_data:
                continue

            # Calculate user balance in the group
            edges = defaultdict(lambda: defaultdict(float), group_data.get("edges", {}))
            graph = Graph(edges)
            group_balances = graph.calculate_balances()
            total_balance += group_balances.get(user_uid, 0.0)
        amount = total_balance
        # Update the label in the UI
        self.ids.net_balance_label.text = f"Your Net Balance in overal: {total_balance:.2f} thousand Tomans\n(or {convert_currency(amount, 'irtt', chand, 'usd'):.2f} USD/ {convert_currency(amount, 'irtt', chand, 'eur'):.2f} EUR/ {convert_currency(amount, 'irtt', chand, 'gbp'):.2f} GBP)"
    
    def logout(self):
        """Log out the current user and clear the session."""
        app = App.get_running_app()
        app.clear_user_session()
        toast("Logged out successfully.")
        self.manager.current = "login"

class NotificationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notifications = []  # List to store active notifications

    def on_enter(self):
        """Refresh the notification list when entering the screen."""
        self.refresh_notifications()

    def refresh_notifications(self):
        """Fetch due recurring bills and update notifications."""
        self.notifications.clear()
        self.clear_notification_widgets()
        
        user_uid = App.get_running_app().user_uid
        current_date = datetime.now()

        # Fetch groups the user belongs to
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        groups = user_groups_ref.get() or {}

        for group_name in groups:
            group_ref = db.reference(f"groups/{group_name}/recurring_bills")
            recurring_bills_data = group_ref.get()

            if not recurring_bills_data:
                continue

            # Handle both dictionary and list structures for recurring bills
            if isinstance(recurring_bills_data, dict):
                for bill_id, bill_data in recurring_bills_data.items():
                    self.add_due_bill(group_name, bill_id, bill_data, current_date)
            elif isinstance(recurring_bills_data, list):
                for bill_id in recurring_bills_data:
                    bill_data = db.reference(f"groups/{group_name}/recurring_bills/{bill_id}").get()
                    if bill_data:
                        self.add_due_bill(group_name, bill_id, bill_data, current_date)

        # Refresh the UI with notifications
        self.show_notifications()

    def add_due_bill(self, group_name, bill_id, bill_data, current_date):
        """Add a bill to the notification list if it's due."""
        try:
            # Ensure `next_due_date` is a valid string
            next_due_date = bill_data.get("next_due_date")
            if isinstance(next_due_date, datetime):
                next_due_date = next_due_date.strftime("%Y-%m-%d")
            elif not isinstance(next_due_date, str):
                return  # Skip invalid dates

            # Parse `next_due_date` and check if it's due
            next_due_date = datetime.strptime(next_due_date, "%Y-%m-%d")
            if next_due_date > current_date:
                return  # Skip bills that are not due

            self.notifications.append({
                "group_name": group_name,
                "bill_id": bill_id,
                "bill_data": bill_data,
            })
        except Exception as e:
            print(f"Error adding due bill: {e}")

    def show_notifications(self):
        """Display notifications on the screen."""
        self.clear_notification_widgets()

        for notification in self.notifications:
            bill_data = notification["bill_data"]
            group_name = notification["group_name"]
            bill_id = notification["bill_id"]

            category = bill_data.get("category", "Uncategorized")
            amount = bill_data.get("amount", 0.0)
            next_due_date = bill_data.get("next_due_date", "Unknown Date")
            message = f"{category}: {amount} USD - Due {next_due_date} in {group_name}"

            def confirm_callback(instance, notif=notification):
                self.confirm_notification(notif)

            def dismiss_callback(instance, notif=notification):
                self.dismiss_notification(notif)

            def edit_callback(instance, notif=notification):
                self.edit_recurring_bill(
                    notif["group_name"], notif["bill_data"], notif["bill_id"]
                )

            # Add the notification widget with the Edit option
            self.add_notification_widget(message, confirm_callback, dismiss_callback, edit_callback)


    def confirm_notification(self, notification):
        """Handle confirmation of a notification."""
        group_name = notification["group_name"]
        bill_id = notification["bill_id"]
        bill_data = notification["bill_data"]

        try:
            # Update the next due date
            bill = Bill(
                payer=bill_data["payer"],
                amount=bill_data["amount"],
                participants=bill_data["participants"],
                frequency=bill_data["frequency"],
                next_due_date=bill_data.get("next_due_date"),
                category=bill_data.get("category", "Uncategorized"),
                split_type=bill_data.get("split_type", "Equally"),
                description=bill_data.get("description", ""),
            )
            bill.update_next_due_date()
            db.reference(f"groups/{group_name}/recurring_bills/{bill_id}").update({
                "next_due_date": bill.next_due_date.strftime("%Y-%m-%d")
            })
        except Exception as e:
            print(f"Error confirming notification: {e}")

        # Remove the notification from the list and refresh UI
        self.notifications.remove(notification)
        self.show_notifications()

    def dismiss_notification(self, notification):
        """Remove the notification from the list without making changes."""
        self.notifications.remove(notification)
        self.show_notifications()

    def add_notification_widget(self, message, confirm_callback, dismiss_callback, edit_callback):
        """Add a notification widget to the UI."""
        layout = self.ids.notification_list
        notification_item = NotificationItem()
        notification_item.ids.message_label.text = message
        notification_item.ids.confirm_button.bind(on_release=confirm_callback)
        notification_item.ids.dismiss_button.bind(on_release=dismiss_callback)
        notification_item.ids.edit_button.bind(on_release=edit_callback)
        layout.add_widget(notification_item)


    def clear_notification_widgets(self):
        """Clear all notification widgets from the UI."""
        self.ids.notification_list.clear_widgets()
    
    def edit_recurring_bill(self, group_name, bill_data, bill_id):
        """Pre-fill the Add Recurring Bill screen with the selected bill."""
        bill = Bill(**bill_data)
        global the_group

        # Fetch the group data
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        # Extract recurring bills
        recurring_bills = group_data.get("recurring_bills", {})

        # Initialize `the_group` with the correct group data
        the_group = Group(
            name=group_name,
            members=group_data.get("members", {}),
            edges=defaultdict(lambda: defaultdict(float), group_data.get("edges", {})),
            recurring_bills=list(recurring_bills.values()),  # Convert to list if needed
            category_totals=defaultdict(float, group_data.get("category_totals", {})),
        )

        # Pre-fill the form with the bill's data
        add_bill_screen = self.manager.get_screen("add_recurring_bill_screen")
        add_bill_screen.prefill_form(group_name, bill)
        
        # Navigate to the "Add Recurring Bill" screen
        self.manager.current = "add_recurring_bill_screen"

class NotificationItem(MDBoxLayout):
    pass

class ParticipantListItem(OneLineAvatarIconListItem):
    uid = StringProperty("")

    def toggle_participant(self):
        """Toggle participant selection through AddExpenseScreen."""
        app = App.get_running_app()
        add_expense_screen = app.root.get_screen("add_expense_screen")
        add_expense_screen.toggle_participant(self.uid)

class ParticipantDialogContent(MDBoxLayout):
    """Content for the participant selection dialog."""
    pass

class MyScreenManager(ScreenManager):
    pass

class MeloSplit(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.payer = ""
        self.payee = ""
        self.amount = 0

    def build(self):
        LabelBase.register(name='MyFont1', fn_regular='Gilroy-Heavy.ttf') # Set custom font styles for KivyMD 
        LabelBase.register(name='MyFont2', fn_regular='Gilroy-Bold.ttf') # Set custom font styles for KivyMD 
        LabelBase.register(name='MyFont3', fn_regular='Gilroy-Medium.ttf') # Set custom font styles for KivyMD 
        LabelBase.register(name='MyFont4', fn_regular='Gilroy-Light.ttf') # Set custom font styles for KivyMD 
        self.theme_cls.font_styles["H4"] = ["MyFont1", 40, False, 0.15] 
        self.theme_cls.font_styles["H6"] = ["MyFont2", 20, False, 0.15] 
        self.theme_cls.font_styles["Body1"] = ["MyFont3", 16, False, -0.05]
        self.user_uid = None  # Initialize user UID
        self.user_email = None  # Initialize user email
        root = MyScreenManager()  # Initialize root first
        self.root = root  # Assign the root widget to the app
        self.check_saved_session()  # Check session after root initialization
        return root


    def check_saved_session(self):
        """Check for a saved session and auto-login the user if valid."""
        if os.path.exists("user_session.json"):
            with open("user_session.json", "r") as session_file:
                session_data = json.load(session_file)
                self.user_uid = session_data.get("user_uid")
                self.user_email = session_data.get("user_email")

                # Verify user exists in Firebase
                user_ref = db.reference(f"/users/{self.user_uid}")
                if user_ref.get():
                    toast(f"Welcome back, {self.user_email}!")
                    self.root.current = "group_manager"  # Navigate to the main screen
                else:
                    # Invalid session, clear it
                    self.clear_user_session()
                    self.root.current = "login"  # Navigate to login screen
        else:
            # No session file exists, navigate to login screen
            self.root.current = "login"


    def clear_user_session(self):
        """Clear the saved user session and navigate to login."""
        if os.path.exists("user_session.json"):
            os.remove("user_session.json")

        self.user_uid = None
        self.user_email = None

if __name__ == "__main__":
    MeloSplit().run()
