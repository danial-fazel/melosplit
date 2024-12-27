from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screen import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
import re
from kivymd.toast import toast
from logic import Graph, Group, Bill
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty
from datetime import datetime
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineListItem

# Firebase imports
import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate("melosplit-firebase.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://melosplit-default-rtdb.firebaseio.com/"
})

def add_user_to_firebase(email, name):
    at_sign = email.find('@')
    uid = email[:at_sign] ##
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


class LoginScreen(MDScreen):
    def login(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()
        
        # Convert email to a safe key
        # safe_email = re.sub(r'[.#$/\[\]]', '_', email)
        at_sign = email.find('@') ##
        safe_email = email[:at_sign]

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

        # # Convert email to a safe key
        # safe_email = re.sub(r'[.#$/\[\]]', '_', email)
        at_sign = email.find('@') ##
        safe_email = email[:at_sign]

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

        App.get_running_app().root.current = "group_manager" ##

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
            # Properly handle the button instance passed by on_release
            group_list.add_widget(
                MDRaisedButton(
                    text=group_name,
                    on_release=lambda btn, group=group_name: self.go_to_group_screen(group),
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
        """Set group title and load transaction history when entering the screen."""
        group_name = App.get_running_app().group_name
        self.ids.group_title.text = f"Group: {group_name}"
        self.transactions_history()

    def transactions_history(self):
        """Load and display transaction history."""
        group_name = App.get_running_app().group_name
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()

        for transaction_id, transaction in transactions.items():
            if isinstance(transaction, dict):  # Ensure transaction is a dictionary
                transaction_widget = TransactionHistoryWidget(
                    payer=transaction.get("payer", "Unknown"),
                    participants=", ".join(transaction.get("participants", [])),
                    amount=str(transaction.get("amount", 0)),
                    description=transaction.get("description", "No description"),
                    date=transaction.get("date", "Unknown"),
                )
                transactions_history.add_widget(transaction_widget)
            else:
                toast(f"Invalid transaction format: {transaction_id}")


    def members_summary(self):
        pass

    def add_expences(self):
        pass

    def settle_ups(Self):
        pass

class TransactionHistoryWidget(MDBoxLayout):
    payer = StringProperty()
    participants = StringProperty()
    amount = StringProperty()
    description = StringProperty()
    date = StringProperty()


class MemberSummaryScreen(Screen):
    def on_enter(self):
        """Populate the screen with member data when the screen is entered."""
        self.populate_member_summary()

    def populate_member_summary(self):
        """Get the group summary and display the member balances."""
        # Get the group summary
        group_name = App.get_running_app().group_name
        group = db.reference(f"groups/{group_name}")
        
        summary = group.get_summary()
        balances = group.get_balances()

        # Clear existing content
        self.ids.member_list.clear_widgets()

        # Add each member's information
        for member, balance in balances.items():
            member_summary = f"{member}: Net Balance: {balance:.2f}"
            contribution = summary["per_member_contributions"].get(member, 0)
            member_summary += f", Contribution: {contribution:.2f}"

            # Create a label for the member's data and add it to the list
            self.ids.member_list.add_widget(
                MDLabel(text=member_summary, theme_text_color="Secondary", size_hint_y=None, height="40dp")
            )

        # Display total expenses
        total_expenses = summary["total_expenses"]
        self.ids.total_expenses_label.text = f"Total Expenses: {total_expenses:.2f}"

        # Optional: Add category breakdown
        category_summary = summary["category_summary"]
        self.ids.category_summary_label.text = "Category Summary: " + ", ".join(
            [f"{category}: {amount:.2f}" for category, amount in category_summary.items()]
        )
        
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

    def open_participants_dialog(self):
        def populate_dialog(*args):
            participant_list = self.participants_dialog.content_cls.ids.participant_list
            participant_list.clear_widgets()

            # Fetch group data and populate the list
            group_name = App.get_running_app().group_name
            group_ref = db.reference(f"groups/{group_name}")
            group_data = group_ref.get()

            if group_data and "members" in group_data:
                for uid, name in group_data["members"].items():
                    print(f"Adding participant: {name} (UID: {uid})")
                    participant_item = ParticipantListItem(uid=uid, text=name)
                    participant_list.add_widget(ParticipantListItem(uid="test", text="Test User"))


        # Create the dialog
        if not hasattr(self, "participants_dialog") or not self.participants_dialog:
            self.participants_dialog = MDDialog(
                title="Select Participants",
                type="custom",
                content_cls=ParticipantDialogContent(),
                buttons=[
                    MDRaisedButton(
                        text="CLOSE", on_release=lambda _: self.participants_dialog.dismiss()
                    ),
                ],
            )
            self.participants_dialog.bind(on_open=populate_dialog)

        # Open the dialog
        self.participants_dialog.open()





    def toggle_participant(self, checkbox, uid):
        """Toggle participant selection."""
        if checkbox.active:
            self.selected_participants.add(uid)
        else:
            self.selected_participants.discard(uid)

        # Update selected participants label
        participant_names = ", ".join(self.selected_participants)
        self.ids.selected_participants_label.text = f"Selected Participants: {participant_names}"



    def add_expense(self):
        """Add expense using logic and save it to Firebase."""
        payer = self.ids.payer_name.text.strip()
        amount = self.ids.amount.text.strip()
        split_type = self.ids.split_type.text.strip()
        category = self.ids.category.text.strip()
        description = self.ids.description.text.strip()

        if not payer or not amount or not split_type or not category:
            self.ids.error_label.text = "All fields except description are required!"
            return

        if not self.selected_participants:
            self.ids.error_label.text = "At least one participant must be selected!"
            return

        # Convert amount to float
        try:
            amount = float(amount)
        except ValueError:
            self.ids.error_label.text = "Invalid amount!"
            return

        # Prepare custom splits or percentages for specific modes
        custom_splits = {}
        if split_type in ["By Shares", "By Percentage"]:
            for uid in self.selected_participants:
                input_id = f"{'share' if split_type == 'By Shares' else 'percentage'}_{uid}"
                try:
                    value = float(self.ids[input_id].text.strip())
                    custom_splits[uid] = value
                except (KeyError, ValueError):
                    self.ids.error_label.text = f"Invalid value for participant {uid}!"
                    return

        # Initialize or load the group graph
        group_name = App.get_running_app().group_name
        group_graph = self.get_group_graph(group_name)

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

    def get_group_graph(self, group_name):
        """Retrieve or initialize the graph for a specific group."""
        group_ref = db.reference(f"groups/{group_name}/graph")
        group_graph = Graph()
        return group_graph

    def clear_inputs(self):
        """Clear all input fields."""
        self.ids.payer_name.text = ""
        self.ids.amount.text = ""
        self.ids.split_type.text = ""
        self.ids.category.text = ""
        self.ids.description.text = ""
        self.selected_participants.clear()

    def highlight_selected_participants(self):
        pass


class SettleUpScreen(Screen):
    """in the main screen using minimize cash flow func of the logic to dispaly the simplified transactions and a key to add expence as in payer and the payee for settling debts"""
    pass

class UserProfileScreen():
    """calculating and showing the user net balance in all their groups,the ability to change password and log out"""
    pass



class ParticipantListItem(OneLineAvatarIconListItem):
    uid = StringProperty("")
    text = StringProperty("")

    def toggle_participant(self):
        """Toggle this participant in AddExpenseScreen."""
        screen = App.get_running_app().root.get_screen("add_expense_screen")  # Get the AddExpenseScreen
        if self.uid in screen.selected_participants:
            screen.selected_participants.remove(self.uid)
            self.ids.checkbox.icon = "checkbox-blank-outline"  # Uncheck
        else:
            screen.selected_participants.add(self.uid)
            self.ids.checkbox.icon = "checkbox-marked"  # Check




class ParticipantDialogContent(MDBoxLayout):
    """Content for the participant selection dialog."""
    pass


class MyScreenManager(ScreenManager):
    pass

class MeloSplit(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.participants_dialog = None

    def show_participants_dialog(self):
        # Load dialog if not already loaded
        if not self.participants_dialog:
            self.participants_dialog = MDDialog(
                title="Select Participants",
                type="custom",
                content_cls=ParticipantDialogContent(),
                buttons=[
                    MDRaisedButton(text="CANCEL", on_release=self.close_dialog),
                    MDRaisedButton(text="OK", on_release=self.submit_participants),
                ],
            )
        # Populate the list
        self.populate_participants()
        self.participants_dialog.open()

    def populate_participants(self):
        participant_list = self.participants_dialog.content_cls.ids.participant_list
        participant_list.clear_widgets()  # Clear old data

        participants = {
            "dani": "Dani",
            "emad": "Emad",
            "melo": "Melo",
            "mhdi": "Mhdi",
        }

        # Dynamically add participants to the list
        for uid, name in participants.items():
            item = OneLineListItem(text=name)
            participant_list.add_widget(item)

    def close_dialog(self, *args):
        if self.participants_dialog:
            self.participants_dialog.dismiss()

    def submit_participants(self, *args):
        # Logic to handle submission of selected participants
        print("Participants submitted (TODO)")


    def set_dropdown_value(self, selected_value):
        self.root.ids.split_type.text = selected_value
        self.root.ids.split_type_menu.dismiss()

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        return MyScreenManager()

if __name__ == "__main__":
    MeloSplit().run()

